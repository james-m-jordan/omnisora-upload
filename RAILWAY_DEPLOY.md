# Railway Deployment Instructions

## Quick Deploy to Railway

### 1. Push to GitHub

First, create a new repository on GitHub:

```bash
cd /Users/jimjordan/Documents/free-omni-sora-final-fix/unified-omni-sora

# Initialize git and add files
git init
git add .
git commit -m "Initial commit - OmniSora unified upload system"

# Create repo on GitHub and push
gh repo create omnisora-upload --public --source=. --remote=origin --push
```

### 2. Deploy on Railway

1. Go to [Railway](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `james-m-jordan/omnisora-upload`
5. Railway will automatically detect the configuration

### 3. Configure Environment Variables

In Railway dashboard, go to Variables and add:

```
B2_KEY_ID=(your B2 key ID)
B2_APPLICATION_KEY=(your B2 application key)
B2_BUCKET=freeload-uploads
B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
OPENAI_API_KEY=(your OpenAI API key)
```

**Important**: Use the actual values from your `.env` file - don't commit secrets to GitHub!

### 4. Configure B2 CORS

In your Backblaze B2 bucket settings:
- Select "Share everything in this bucket with all HTTPS origins"
- Apply CORS rules to: "S3 Compatible API"

Or for specific domain after deployment:
- Share with one origin: `https://your-app.railway.app`

### 5. Update Frontend URL

After deployment, update the `FRONTEND_URL` environment variable in Railway with your actual domain.

## What's Included

- ✅ 10TB file upload support
- ✅ AI-powered tagging with OpenAI
- ✅ Beautiful SORA-inspired dark UI
- ✅ Hash-based file sharing
- ✅ SQLite database for metadata
- ✅ Automatic frontend build on deploy
- ✅ Health check endpoint at `/health`

## Troubleshooting

If deployment fails:
1. Check Railway build logs
2. Ensure all environment variables are set
3. Verify B2 CORS settings allow your Railway domain
4. Check that the OpenAI API key is valid

## Local Development

To run locally:
```bash
npm run dev
```

This will start both backend (port 5000) and frontend (port 5173).