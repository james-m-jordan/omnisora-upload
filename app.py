import os
import hashlib
import sqlite3
import logging
import re
from flask import Flask, request, jsonify, render_template_string, render_template, Response, url_for, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from boto3.session import Session
from dotenv import load_dotenv
from io import BytesIO
from datetime import datetime
import openai
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
BUCKET_NAME = os.getenv('B2_BUCKET', 'my-uploads')
CHUNK_SIZE = 100 * 1024 * 1024  # 100MB chunks
UPLOAD_FOLDER = 'uploads'
DATABASE = 'uploads.db'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'mp4', 'mov', 'avi'}

# Initialize OpenAI client for AI tagging
if os.getenv('OPENAI_API_KEY'):
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize B2 client
session = Session()
s3 = session.client(
    service_name='s3',
    endpoint_url=os.getenv('B2_ENDPOINT'),
    aws_access_key_id=os.getenv('B2_KEY_ID'),
    aws_secret_access_key=os.getenv('B2_APPLICATION_KEY'),
    config=None
)

# Helper functions
def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def calculate_file_hash_chunked(file_obj, chunk_size=8192):
    """Calculate SHA256 hash of a file using chunked reading to save memory."""
    hasher = hashlib.sha256()
    file_obj.seek(0)
    
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
    
    file_obj.seek(0)  # Reset file pointer
    return hasher.hexdigest()

def generate_ai_tags(description, filename):
    """Generate AI tags based on file description and name."""
    if not os.getenv('OPENAI_API_KEY') or not description:
        return []
    
    try:
        prompt = f"""Given this file description and filename, generate 5-8 relevant tags that would help categorize and find this file later.

Filename: {filename}
Description: {description}

Return only the tags as a JSON array of strings, nothing else."""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates relevant tags for files."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        tags_text = response.choices[0].message.content.strip()
        tags = json.loads(tags_text)
        return tags[:8]  # Limit to 8 tags
    except Exception as e:
        logger.error(f"Error generating AI tags: {e}")
        return []

def upload_large_file_multipart(file_obj, bucket, key, file_size):
    """Upload large files using B2's multipart upload API."""
    try:
        # Initialize multipart upload
        response = s3.create_multipart_upload(
            Bucket=bucket,
            Key=key
        )
        upload_id = response['UploadId']
        logger.info(f"Started multipart upload: {upload_id}")
        
        # Upload parts
        parts = []
        part_number = 1
        bytes_uploaded = 0
        
        file_obj.seek(0)
        
        while bytes_uploaded < file_size:
            # Calculate part size (last part might be smaller)
            remaining = file_size - bytes_uploaded
            part_size = min(CHUNK_SIZE, remaining)
            
            # Read chunk
            chunk_data = file_obj.read(part_size)
            
            logger.info(f"Uploading part {part_number} ({format_file_size(part_size)})")
            
            # Upload part
            response = s3.upload_part(
                Bucket=bucket,
                Key=key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=chunk_data
            )
            
            parts.append({
                'PartNumber': part_number,
                'ETag': response['ETag']
            })
            
            bytes_uploaded += part_size
            part_number += 1
            
            # Log progress
            progress = (bytes_uploaded / file_size) * 100
            logger.info(f"Upload progress: {progress:.1f}% ({format_file_size(bytes_uploaded)}/{format_file_size(file_size)})")
        
        # Complete multipart upload
        response = s3.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        logger.info(f"Multipart upload completed: {key}")
        return True
        
    except Exception as e:
        logger.error(f"Multipart upload error: {e}")
        # Abort the upload if it fails
        try:
            s3.abort_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id
            )
        except:
            pass
        raise e

def init_db():
    """Initialize the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS uploads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  hash TEXT UNIQUE NOT NULL,
                  filename TEXT NOT NULL,
                  size INTEGER,
                  upload_date TEXT NOT NULL,
                  content_type TEXT,
                  description TEXT,
                  tags TEXT,
                  b2_file_id TEXT)''')
    conn.commit()
    conn.close()

def save_file_metadata(file_hash, filename, size, content_type, description=None, tags=None, b2_file_id=None):
    """Save file metadata to database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Convert tags list to JSON string
    tags_json = json.dumps(tags) if tags else '[]'
    
    c.execute('''INSERT OR REPLACE INTO uploads 
                 (hash, filename, size, upload_date, content_type, description, tags, b2_file_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (file_hash, filename, size, datetime.now().isoformat(), content_type, description, tags_json, b2_file_id))
    conn.commit()
    conn.close()

def get_file_metadata(file_hash):
    """Get file metadata from database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM uploads WHERE hash = ?', (file_hash,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'hash': row[1],
            'filename': row[2],
            'size': row[3],
            'upload_date': row[4],
            'content_type': row[5],
            'description': row[6],
            'tags': json.loads(row[7]) if row[7] else [],
            'b2_file_id': row[8]
        }
    return None

def get_recent_uploads(limit=10):
    """Get recent uploads from database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''SELECT hash, filename, size, upload_date, description, tags 
                 FROM uploads 
                 ORDER BY upload_date DESC 
                 LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    
    uploads = []
    for row in rows:
        uploads.append({
            'hash': row[0],
            'filename': row[1],
            'size': row[2],
            'upload_date': row[3],
            'description': row[4],
            'tags': json.loads(row[5]) if row[5] else []
        })
    return uploads

@app.route('/')
def index():
    """Serve the main upload interface."""
    # In production, serve the built React app
    if os.path.exists('frontend/dist/index.html'):
        return send_from_directory('frontend/dist', 'index.html')
    # In development, redirect to Vite dev server
    return render_template('index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the React build."""
    if os.path.exists(f'frontend/dist/{path}'):
        return send_from_directory('frontend/dist', path)
    # Fallback to index.html for client-side routing
    return send_from_directory('frontend/dist', 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload with AI tagging."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    description = request.form.get('description', '')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Read file into memory
    file_data = BytesIO(file.read())
    file_size = file_data.tell()
    file_data.seek(0)
    
    # Calculate hash
    file_hash = calculate_file_hash_chunked(file_data)
    logger.info(f"File hash: {file_hash}, Size: {format_file_size(file_size)}")
    
    # Check if file already exists
    existing = get_file_metadata(file_hash)
    if existing:
        return jsonify({
            'success': True,
            'hash': file_hash,
            'filename': existing['filename'],
            'size': format_file_size(existing['size']),
            'tags': existing['tags'],
            'message': 'File already exists',
            'shareUrl': f"/f/{file_hash[:8]}"
        })
    
    # Generate AI tags
    tags = generate_ai_tags(description, file.filename)
    
    # Upload to B2
    try:
        key = f"{file_hash}/{secure_filename(file.filename)}"
        
        if file_size > CHUNK_SIZE:
            # Use multipart upload for large files
            logger.info(f"Using multipart upload for large file: {format_file_size(file_size)}")
            upload_large_file_multipart(file_data, BUCKET_NAME, key, file_size)
        else:
            # Use simple upload for smaller files
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=file_data.getvalue(),
                ContentType=file.content_type or 'application/octet-stream'
            )
        
        # Save metadata
        save_file_metadata(
            file_hash,
            file.filename,
            file_size,
            file.content_type,
            description,
            tags
        )
        
        return jsonify({
            'success': True,
            'hash': file_hash,
            'filename': file.filename,
            'size': format_file_size(file_size),
            'tags': tags,
            'shareUrl': f"/f/{file_hash[:8]}"
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/f/<hash_prefix>')
def file_page(hash_prefix):
    """Display file information and download link."""
    # Find file by hash prefix
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT * FROM uploads WHERE hash LIKE ?', (hash_prefix + '%',))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "File not found", 404
    
    file_info = {
        'hash': row[1],
        'filename': row[2],
        'size': format_file_size(row[3]),
        'upload_date': row[4],
        'content_type': row[5],
        'description': row[6],
        'tags': json.loads(row[7]) if row[7] else []
    }
    
    return render_template('file_view.html', file=file_info)

@app.route('/download/<file_hash>')
def download_file(file_hash):
    """Generate presigned URL for file download."""
    metadata = get_file_metadata(file_hash)
    if not metadata:
        return "File not found", 404
    
    try:
        key = f"{file_hash}/{metadata['filename']}"
        
        # Generate presigned URL
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=3600  # 1 hour
        )
        
        return jsonify({
            'success': True,
            'download_url': url,
            'filename': metadata['filename']
        })
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent')
def recent_uploads():
    """Get recent uploads."""
    uploads = get_recent_uploads(20)
    return jsonify(uploads)

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Initialize database on startup
init_db()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)