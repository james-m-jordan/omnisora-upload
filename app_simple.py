import os
import hashlib
import sqlite3
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from boto3.session import Session
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
B2_KEY_ID = os.getenv('B2_KEY_ID')
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY')
B2_BUCKET = os.getenv('B2_BUCKET', 'freeload-uploads')
B2_ENDPOINT = os.getenv('B2_ENDPOINT', 'https://s3.us-east-005.backblazeb2.com')

# Validate environment variables
if not all([B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET, B2_ENDPOINT]):
    logger.error("Missing required B2 environment variables!")
    logger.error(f"B2_KEY_ID: {'SET' if B2_KEY_ID else 'MISSING'}")
    logger.error(f"B2_APPLICATION_KEY: {'SET' if B2_APPLICATION_KEY else 'MISSING'}")
    logger.error(f"B2_BUCKET: {B2_BUCKET}")
    logger.error(f"B2_ENDPOINT: {B2_ENDPOINT}")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Database setup
DB_PATH = 'metadata.db'

def init_db():
    """Initialize the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT NOT NULL,
                  original_filename TEXT,
                  filehash TEXT NOT NULL,
                  file_size INTEGER,
                  mime_type TEXT,
                  url TEXT NOT NULL,
                  upload_date TEXT,
                  download_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()

# Initialize B2 client
try:
    session = Session()
    s3 = session.client(
        service_name='s3',
        endpoint_url=B2_ENDPOINT,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APPLICATION_KEY
    )
    logger.info("B2 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize B2 client: {e}")
    s3 = None

def calculate_file_hash(file_obj):
    """Calculate SHA256 hash of file."""
    hasher = hashlib.sha256()
    file_obj.seek(0)
    while chunk := file_obj.read(8192):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()

def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes is None:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

@app.route('/')
def index():
    """Serve the main page."""
    if os.path.exists('frontend/dist/index.html'):
        return send_from_directory('frontend/dist', 'index.html')
    return render_template('index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    if os.path.exists(f'frontend/dist/{path}'):
        return send_from_directory('frontend/dist', path)
    return send_from_directory('frontend/dist', 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    if not s3:
        return jsonify({'error': 'Storage not configured. Check environment variables.'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Get file info
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        # Calculate hash
        file_hash = calculate_file_hash(file)
        logger.info(f"Uploading file: {file.filename}, hash: {file_hash[:8]}, size: {format_file_size(file_size)}")
        
        # Upload to B2
        safe_filename = secure_filename(file.filename)
        s3_key = f"{file_hash[:8]}_{safe_filename}"
        
        s3.upload_fileobj(
            Fileobj=file,
            Bucket=B2_BUCKET,
            Key=s3_key
        )
        
        # Construct URL
        url = f"https://f005.backblazeb2.com/file/{B2_BUCKET}/{s3_key}"
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO files 
                    (filename, original_filename, filehash, file_size, mime_type, url, upload_date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (s3_key, file.filename, file_hash, file_size, file.mimetype, url, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'hash': file_hash,
            'filename': file.filename,
            'size': format_file_size(file_size),
            'shareUrl': f"/f/{file_hash[:8]}"
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/f/<hash_prefix>')
def view_file(hash_prefix):
    """View file by hash."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM files WHERE filehash LIKE ?', (hash_prefix + '%',))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "File not found", 404
    
    file_info = {
        'filename': row[2],
        'hash': row[3],
        'size': format_file_size(row[4]),
        'url': row[6],
        'upload_date': row[7]
    }
    
    return render_template('file_view.html', file=file_info)

@app.route('/download/<hash_prefix>')
def download_file(hash_prefix):
    """Generate download URL."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT url FROM files WHERE filehash LIKE ?', (hash_prefix + '%',))
    row = c.fetchone()
    
    # Update download count
    c.execute('UPDATE files SET download_count = download_count + 1 WHERE filehash LIKE ?', (hash_prefix + '%',))
    conn.commit()
    conn.close()
    
    if not row:
        return jsonify({'error': 'File not found'}), 404
    
    return jsonify({'url': row[0]})

@app.route('/api/recent')
def recent_files():
    """Get recent uploads."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT filehash, original_filename, file_size, upload_date 
                 FROM files ORDER BY upload_date DESC LIMIT 20''')
    rows = c.fetchall()
    conn.close()
    
    files = []
    for row in rows:
        files.append({
            'hash': row[0],
            'filename': row[1],
            'size': row[2],
            'upload_date': row[3]
        })
    
    return jsonify(files)

@app.route('/health')
def health():
    """Health check."""
    return jsonify({
        'status': 'healthy',
        'b2_configured': s3 is not None,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 