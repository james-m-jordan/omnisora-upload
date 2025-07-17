import { useState, useRef, useEffect } from 'react'
import { Button } from './components/ui/button.jsx'
import { Textarea } from './components/ui/textarea.jsx'
import { Plus, Send, Download, Loader2, Copy, Check } from 'lucide-react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'system',
      content: 'Welcome! Upload any file and describe it to get a secure download link.',
      timestamp: new Date()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [copiedHash, setCopiedHash] = useState(null)
  const fileInputRef = useRef(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      addMessage('user', `Selected file: ${file.name} (${formatFileSize(file.size)})`)
      
      // Add system message prompting for description
      setTimeout(() => {
        addMessage('system', 'Please describe what this file contains to help with tagging:')
      }, 500)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const addMessage = (type, content, extra = {}) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      type,
      content,
      timestamp: new Date(),
      ...extra
    }])
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopiedHash(text)
    setTimeout(() => setCopiedHash(null), 2000)
  }

  const handleSubmit = async () => {
    if (!selectedFile || !inputValue.trim()) return

    const description = inputValue.trim()
    setInputValue('')
    
    // Add user's description message
    addMessage('user', description)
    
    setIsUploading(true)
    addMessage('system', 'Uploading your file and generating tags...')

    try {
      // If file is small (<4MB) keep existing flow
      if (selectedFile.size < 4.5 * 1024 * 1024) {
        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('description', description)

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        })

        const data = await response.json()

        if (!data.success) throw new Error(data.error || 'Upload failed')

        addMessage('system', "Upload complete! Here's your file info:", {
          uploadData: {
            hash: data.hash,
            tags: data.tags,
            downloadUrl: data.downloadUrl,
            shareableUrl: data.shareableUrl || data.downloadUrl
          }
        })
        setSelectedFile(null)
      } else {
        // LARGE FILE FLOW --------------------------------------------------
        // 1. Compute hashes (sha256 for id, sha1 for B2 integrity)
        const arrayBuf = await selectedFile.arrayBuffer()
        const sha256Buf = await window.crypto.subtle.digest('SHA-256', arrayBuf)
        const sha1Buf = await window.crypto.subtle.digest('SHA-1', arrayBuf)
        const bufToHex = (buffer) => Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('')
        const sha256Hex = bufToHex(sha256Buf)
        const sha1Hex = bufToHex(sha1Buf)
        const shortHash = sha256Hex.slice(0, 12)

        // 2. Request an upload URL from backend
        const initResp = await fetch('/api/get-upload-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fileName: selectedFile.name, hash: shortHash })
        })
        const initData = await initResp.json()
        if (!initResp.ok) throw new Error(initData.error || 'Failed to get upload URL')

        // 3. Upload directly to Backblaze
        const uploadRes = await fetch(initData.uploadUrl, {
          method: 'POST',
          headers: {
            Authorization: initData.authorizationToken,
            'X-Bz-File-Name': initData.b2FileName,
            'Content-Type': selectedFile.type || 'application/octet-stream',
            'Content-Length': selectedFile.size.toString(),
            'X-Bz-Content-Sha1': sha1Hex
          },
          body: selectedFile
        })

        const uploadJson = await uploadRes.json()
        if (!uploadRes.ok) throw new Error(uploadJson.message || 'B2 upload failed')

        // 4. Finalize + metadata
        const finalizeResp = await fetch('/api/finalize-upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            hash: shortHash,
            description,
            originalFilename: selectedFile.name,
            size: selectedFile.size,
            mimetype: selectedFile.type,
            bucketId: initData.bucketId,
            b2FileName: initData.b2FileName,
            b2FileId: uploadJson.fileId
          })
        })
        const finalizeData = await finalizeResp.json()
        if (!finalizeResp.ok) throw new Error(finalizeData.error || 'Failed to finalize upload')

        addMessage('system', "Upload complete! Here's your file info:", {
          uploadData: {
            hash: finalizeData.hash,
            tags: finalizeData.tags,
            downloadUrl: finalizeData.downloadUrl,
            shareableUrl: finalizeData.shareableUrl || finalizeData.downloadUrl
          }
        })
        setSelectedFile(null)
      }
    } catch (error) {
      addMessage('system', `Error: ${error.message}`, { error: true })
    } finally {
      setIsUploading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <h1 className="text-xl font-semibold text-center">Freeload</h1>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-2 ${
                message.type === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : message.error
                  ? 'bg-destructive/10 text-destructive'
                  : 'bg-muted'
              }`}
            >
              <p className="text-sm">{message.content}</p>
              
              {/* Upload result display */}
              {message.uploadData && (
                <div className="mt-3 space-y-3 bg-background/50 rounded p-3">
                  <div className="space-y-1">
                    <span className="text-xs font-medium">Shareable Link:</span>
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-background px-2 py-1 rounded flex-1 overflow-x-auto whitespace-nowrap">
                        {message.uploadData.shareableUrl || message.uploadData.downloadUrl}
                      </code>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(message.uploadData.shareableUrl || message.uploadData.downloadUrl)}
                        className="h-6 w-6 p-0 shrink-0"
                      >
                        {copiedHash === (message.uploadData.shareableUrl || message.uploadData.downloadUrl) ? (
                          <Check className="h-3 w-3" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Share this link to download the file (hash: {message.uploadData.hash})
                    </p>
                  </div>
                  
                  <div>
                    <span className="text-xs font-medium">AI Tags:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {message.uploadData.tags.map((tag, i) => (
                        <span
                          key={i}
                          className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div className="pt-1 border-t">
                    <a
                      href={message.uploadData.downloadUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <Download className="h-3 w-3" />
                      Test download link
                    </a>
                  </div>
                </div>
              )}
              
              <span className="text-xs opacity-60 mt-1 block">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="max-w-3xl mx-auto">
          {selectedFile && (
            <div className="mb-2 text-sm text-muted-foreground">
              Ready to upload: {selectedFile.name}
            </div>
          )}
          
          <div className="flex gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              className="hidden"
              accept="*/*"
            />
            
            <Button
              size="icon"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="shrink-0"
            >
              <Plus className="h-4 w-4" />
            </Button>
            
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                selectedFile 
                  ? "Describe your file..." 
                  : "Click + to select a file first"
              }
              disabled={!selectedFile || isUploading}
              className="min-h-[40px] max-h-[120px] resize-none"
              rows={1}
            />
            
            <Button
              size="icon"
              onClick={handleSubmit}
              disabled={!selectedFile || !inputValue.trim() || isUploading}
              className="shrink-0"
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          <p className="text-xs text-muted-foreground text-center mt-2">
            Free uploads • Your data helps improve our tagging AI
          </p>
        </div>
      </div>
    </div>
  )
}

export default App

