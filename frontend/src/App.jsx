import React, { useState, useCallback } from 'react';
import { Upload, File, Tag, Share2, Loader2, Check, AlertCircle } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Alert, AlertDescription } from './components/ui/alert';
import { Progress } from './components/ui/progress';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function App() {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);
  const [recentUploads, setRecentUploads] = useState([]);
  const [showRecent, setShowRecent] = useState(false);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);

    try {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          setUploadProgress(percentComplete);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          const result = JSON.parse(xhr.responseText);
          setUploadResult(result);
          setFile(null);
          setDescription('');
          document.getElementById('file-input').value = '';
          fetchRecentUploads();
        } else {
          const errorData = JSON.parse(xhr.responseText);
          setError(errorData.error || 'Upload failed');
        }
        setUploading(false);
      });

      xhr.addEventListener('error', () => {
        setError('Network error occurred');
        setUploading(false);
      });

      xhr.open('POST', `${API_URL}/api/upload`);
      xhr.send(formData);
    } catch (err) {
      setError(err.message);
      setUploading(false);
    }
  };

  const fetchRecentUploads = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/recent`);
      if (response.ok) {
        const data = await response.json();
        setRecentUploads(data);
      }
    } catch (err) {
      console.error('Failed to fetch recent uploads:', err);
    }
  }, []);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(window.location.origin + text);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-12 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
              OmniSora Upload
            </h1>
            <p className="text-xl text-muted-foreground">
              Upload files up to 10TB with AI-powered tagging
            </p>
          </div>

          {/* Upload Card */}
          <Card className="mb-8 border-border bg-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Upload File
              </CardTitle>
              <CardDescription>
                Select a file and provide a description for AI tagging
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="file-input" className="text-sm font-medium">
                  Choose File
                </label>
                <Input
                  id="file-input"
                  type="file"
                  onChange={handleFileSelect}
                  disabled={uploading}
                  className="cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
                />
                {file && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <File className="w-4 h-4" />
                    <span>{file.name}</span>
                    <span className="text-xs">({formatFileSize(file.size)})</span>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label htmlFor="description" className="text-sm font-medium">
                  Description (for AI tagging)
                </label>
                <Textarea
                  id="description"
                  placeholder="Describe your file to help generate relevant tags..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={uploading}
                  className="min-h-[100px] resize-none"
                />
              </div>

              {uploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Uploading...</span>
                    <span>{Math.round(uploadProgress)}%</span>
                  </div>
                  <Progress value={uploadProgress} className="h-2" />
                </div>
              )}

              <Button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="w-full"
              >
                {uploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload File
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Success Result */}
          {uploadResult && (
            <Card className="mb-8 border-green-800 bg-green-950/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-green-400">
                  <Check className="w-5 h-5" />
                  Upload Successful!
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">File: {uploadResult.filename}</p>
                  <p className="text-sm text-muted-foreground">Size: {uploadResult.size}</p>
                  
                  {uploadResult.tags && uploadResult.tags.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium flex items-center gap-2">
                        <Tag className="w-4 h-4" />
                        AI-Generated Tags:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {uploadResult.tags.map((tag, index) => (
                          <Badge key={index} variant="secondary">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-2">
                    <p className="text-sm font-medium mb-2">Share URL:</p>
                    <div className="flex items-center gap-2">
                      <Input
                        value={window.location.origin + uploadResult.shareUrl}
                        readOnly
                        className="font-mono text-sm"
                      />
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => copyToClipboard(uploadResult.shareUrl)}
                      >
                        <Share2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recent Uploads */}
          <Card className="border-border bg-card">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Recent Uploads</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowRecent(!showRecent);
                    if (!showRecent) fetchRecentUploads();
                  }}
                >
                  {showRecent ? 'Hide' : 'Show'}
                </Button>
              </div>
            </CardHeader>
            {showRecent && (
              <CardContent>
                <div className="space-y-3">
                  {recentUploads.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No recent uploads
                    </p>
                  ) : (
                    recentUploads.map((upload) => (
                      <div
                        key={upload.hash}
                        className="p-3 rounded-lg bg-secondary/50 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-sm">{upload.filename}</p>
                          <Badge variant="outline" className="text-xs">
                            {upload.size}
                          </Badge>
                        </div>
                        {upload.description && (
                          <p className="text-xs text-muted-foreground">
                            {upload.description}
                          </p>
                        )}
                        {upload.tags && upload.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {upload.tags.map((tag, index) => (
                              <Badge key={index} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                        <a
                          href={`/f/${upload.hash.substring(0, 8)}`}
                          className="text-xs text-primary hover:underline"
                        >
                          View file →
                        </a>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

export default App;