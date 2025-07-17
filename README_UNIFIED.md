# OmniSora Upload - Unified File Upload System

A powerful file upload system that combines:
- 🚀 **10TB file support** from Omniload
- 🤖 **AI-powered tagging** from Freeload
- 🎨 **Beautiful SORA UI** from OpenAI-Clone

## Features

- Upload files up to 10TB using chunked multipart uploads
- AI-generated tags based on file descriptions (OpenAI integration)
- Hash-based file sharing with short URLs
- Modern, dark-themed UI inspired by OpenAI's SORA
- Recent uploads gallery with metadata
- Progress tracking for large file uploads

## Quick Start

### 1. Prerequisites

- Python 3.11+ (with datasci conda environment)
- Node.js 16+
- Backblaze B2 account
- OpenAI API key (optional, for AI tagging)

### 2. Setup Environment

```bash
# Clone and enter the unified project
cd unified-omni-sora

# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# - B2_KEY_ID
# - B2_APPLICATION_KEY
# - B2_BUCKET
# - B2_ENDPOINT
# - OPENAI_API_KEY (optional)
```

### 3. Install Dependencies

```bash
# Install Python dependencies
source ~/miniforge3/etc/profile.d/conda.sh && conda activate datasci
pip install -r requirements.txt

# Install Node dependencies
npm install
cd frontend && npm install && cd ..
```

### 4. Run the Application

```bash
# Development mode (runs both backend and frontend)
npm run dev

# Or run separately:
# Backend only
npm run dev:backend

# Frontend only
npm run dev:frontend
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000

### 5. Production Deployment

For Railway deployment:

```bash
# Build frontend
npm run build

# Start production server
npm run start:prod
```

## Project Structure

```
unified-omni-sora/
├── app_integrated.py      # Flask backend with AI tagging
├── frontend/             # React frontend with SORA UI
│   ├── src/
│   │   ├── App.jsx      # Main application component
│   │   ├── components/  # UI components from SORA
│   │   └── index.css    # SORA-inspired styling
│   └── package.json
├── templates/           # HTML templates for file viewing
├── requirements.txt     # Python dependencies
├── package.json        # Node.js dependencies
└── .env.example       # Environment template
```

## API Endpoints

- `POST /api/upload` - Upload file with description
- `GET /f/<hash>` - View file by hash
- `GET /download/<hash>` - Generate download URL
- `GET /api/recent` - Get recent uploads
- `GET /health` - Health check

## Configuration

### Environment Variables

- `B2_KEY_ID` - Backblaze Key ID
- `B2_APPLICATION_KEY` - Backblaze Application Key
- `B2_BUCKET` - B2 bucket name
- `B2_ENDPOINT` - B2 S3-compatible endpoint
- `OPENAI_API_KEY` - OpenAI API key for tagging (optional)
- `PORT` - Server port (default: 5000)
- `MAX_FILE_SIZE` - Maximum file size in bytes
- `CHUNK_SIZE` - Chunk size for multipart uploads

### Backblaze B2 Setup

1. Create a B2 bucket
2. Generate application keys with read/write permissions
3. Note your endpoint URL (e.g., `https://s3.us-west-000.backblazeb2.com`)
4. Configure CORS if needed for direct browser uploads

## Development Notes

- The backend uses Flask with multipart upload support
- Frontend is built with React + Vite + Tailwind CSS
- AI tagging uses OpenAI's GPT-3.5 when API key is provided
- Files are stored by SHA-256 hash to prevent duplicates
- SQLite database stores metadata locally

## Troubleshooting

1. **Large file uploads failing**: Check your B2 bucket settings and ensure multipart uploads are enabled
2. **AI tagging not working**: Verify your OpenAI API key is valid
3. **CORS errors**: Update the `FRONTEND_URL` in `.env` to match your frontend URL
4. **Database errors**: Ensure the backend has write permissions in the current directory

## License

This project combines code from multiple repositories. Please check individual project licenses.