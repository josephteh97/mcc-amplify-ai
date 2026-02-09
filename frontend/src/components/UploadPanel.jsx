import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const UploadPanel = ({ onJobCreated, onProcessingComplete }) => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | uploading | processing | completed | error
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  const pollIntervalRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Accept PDF or RVT
      const isPdf = selectedFile.name.toLowerCase().endswith('.pdf');
      const isRvt = selectedFile.name.toLowerCase().endswith('.rvt');
      
      if (isPdf || isRvt) {
        setFile(selectedFile);
        setError(null);
        setStatus('idle');
      } else {
        setError('Please select a valid PDF or RVT file');
        setFile(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setStatus('uploading');
    setProgress(10);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Determine endpoint based on file type
      const isRvt = file.name.toLowerCase().endsWith('.rvt');
      const endpoint = isRvt ? '/api/upload-rvt' : '/api/upload';

      const uploadRes = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) throw new Error('Upload failed');
      const { job_id } = await uploadRes.json();
      
      onJobCreated(job_id); // Notify parent
      
      // If PDF, trigger processing
      if (!isRvt) {
        setStatus('processing');
        setProgress(30);
        const processRes = await fetch(`/api/process/${job_id}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_name: file.name.replace('.pdf', '') })
        });
        if (!processRes.ok) throw new Error('Processing start failed');
      } else {
        setStatus('processing'); // RVT also processes (renders)
      }

      startPolling(job_id);

    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  const startPolling = (id) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/status/${id}`);
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.progress) setProgress(data.progress);

        if (data.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          setStatus('completed');
          onProcessingComplete(id, data.result);
        } else if (data.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          setStatus('error');
          setError(data.error || 'Processing failed');
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);
  };

  return (
    <div className="p-4 bg-white rounded-xl shadow-sm border border-gray-100 h-full flex flex-col">
      <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        <Upload size={20} className="text-indigo-600" />
        Upload Project
      </h2>

      <div 
        onClick={() => status === 'idle' && fileInputRef.current?.click()}
        className={`flex-1 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-6 text-center transition-all ${
          status !== 'idle' ? 'bg-gray-50 border-gray-200' : 'border-indigo-200 hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.rvt"
          onChange={handleFileSelect}
          className="hidden"
          disabled={status !== 'idle'}
        />
        
        {file ? (
          <div className="flex flex-col items-center">
            <FileText className="text-indigo-600 mb-2" size={40} />
            <p className="font-medium text-gray-700 truncate max-w-[200px]">{file.name}</p>
            <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        ) : (
          <>
            <Upload className="text-gray-300 mb-3" size={40} />
            <p className="text-gray-500 font-medium">Click to upload PDF or RVT</p>
          </>
        )}
      </div>

      {file && status === 'idle' && (
        <button
          onClick={handleUpload}
          className="mt-4 w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition-colors"
        >
          Process File
        </button>
      )}

      {status === 'processing' || status === 'uploading' ? (
        <div className="mt-4">
          <div className="flex justify-between text-xs font-medium text-gray-600 mb-1">
            <span className="flex items-center gap-1">
              <Loader className="animate-spin" size={12} />
              Processing...
            </span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300" 
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      ) : null}

      {status === 'completed' && (
        <div className="mt-4 p-3 bg-green-50 text-green-700 rounded-lg flex items-center gap-2 text-sm font-medium">
          <CheckCircle size={16} />
          <span>Success! Model ready.</span>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default UploadPanel;
