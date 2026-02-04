import React, { useState, useRef, useEffect } from 'react';
import { Upload, Play, Loader, CheckCircle, AlertCircle, Download } from 'lucide-react';

const App = () => {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | uploading | processing | completed | error
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // Clean up polling on unmount
  const pollIntervalRef = useRef(null);
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
      setStatus('idle');
    } else {
      setError('Please select a valid PDF file');
      setFile(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setStatus('uploading');
    setProgress(5);
    setMessage('Uploading file to server...');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // 1. Upload the file
      const uploadRes = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) throw new Error('Upload failed. Please try again.');
      const { job_id } = await uploadRes.json();
      setJobId(job_id);
      
      // 2. Trigger processing
      setMessage('Starting AI analysis...');
      const processRes = await fetch(`/api/process/${job_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: file.name.replace('.pdf', '') })
      });

      if (!processRes.ok) throw new Error('Failed to start processing.');

      setStatus('processing');
      startPolling(job_id);
    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  const startPolling = (id) => {
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/status/${id}`);
        if (!response.ok) return;
        
        const data = await response.json();
        setProgress(data.progress || 0);
        setMessage(data.message || 'Processing floor plan...');

        if (data.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          setStatus('completed');
          setProgress(100);
          setMessage('3D Model generated successfully!');
        } else if (data.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          setStatus('error');
          setError(data.error || 'AI processing failed.');
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 p-6 flex flex-col items-center justify-center">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="bg-indigo-600 p-8 text-white">
          <h1 className="text-3xl font-extrabold flex items-center gap-3">
            Amplify Floor Plan AI
          </h1>
          <p className="text-indigo-100 mt-2">
            Transform 2D PDF blueprints into interactive 3D BIM models
          </p>
        </div>

        <div className="p-8">
          {/* Dropzone/Selector */}
          <div 
            onClick={() => status === 'idle' && fileInputRef.current?.click()}
            className={`border-3 border-dashed rounded-xl p-10 text-center transition-all ${
              status !== 'idle' ? 'bg-gray-50 border-gray-200 cursor-not-allowed' : 
              'border-indigo-200 hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={handleFileSelect}
              className="hidden"
              disabled={status !== 'idle'}
            />
            <Upload className={`mx-auto h-14 w-14 mb-4 ${file ? 'text-indigo-600' : 'text-gray-300'}`} />
            <p className="text-lg font-medium text-gray-700">
              {file ? file.name : 'Click to upload your PDF blueprint'}
            </p>
            <p className="text-sm text-gray-500 mt-1">Maximum file size: 25MB</p>
          </div>

          {/* Action Button */}
          {file && status === 'idle' && (
            <button
              onClick={handleUpload}
              className="w-full mt-6 bg-indigo-600 text-white py-4 rounded-xl hover:bg-indigo-700 flex items-center justify-center gap-3 font-bold shadow-lg shadow-indigo-200 transition-all"
            >
              <Play size={20} fill="currentColor" />
              Generate 3D Model
            </button>
          )}

          {/* Status/Progress Display */}
          {(status === 'processing' || status === 'uploading') && (
            <div className="mt-8 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-indigo-700 font-semibold">
                  <Loader className="animate-spin" size={20} />
                  <span>{message}</span>
                </div>
                <span className="text-sm font-bold text-indigo-600">{progress}%</span>
              </div>
              <div className="w-full bg-indigo-100 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-indigo-600 h-full transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-6 p-4 bg-red-50 border-l-4 border-red-500 rounded flex items-start gap-3">
              <AlertCircle className="text-red-500 shrink-0" size={20} />
              <p className="text-sm text-red-800 font-medium">{error}</p>
            </div>
          )}

          {/* Success / Result Actions */}
          {status === 'completed' && (
            <div className="mt-8 animate-in fade-in zoom-in duration-300">
              <div className="p-4 bg-green-50 border border-green-200 rounded-xl flex items-center gap-4 mb-6">
                <div className="bg-green-500 p-2 rounded-full">
                  <CheckCircle className="text-white" size={24} />
                </div>
                <div>
                  <h4 className="font-bold text-green-900">Conversion Complete!</h4>
                  <p className="text-green-700 text-sm">Your BIM model is ready for download.</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <a
                  href={`/api/download/gltf/${jobId}`}
                  className="flex items-center justify-center gap-2 bg-indigo-600 text-white py-4 rounded-xl hover:bg-indigo-700 font-bold shadow-md"
                >
                  <Download size={20} />
                  Download GLTF
                </a>
                <button
                  onClick={() => window.location.reload()}
                  className="border-2 border-gray-200 text-gray-600 py-4 rounded-xl hover:bg-gray-50 font-bold"
                >
                  Reset
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <p className="mt-6 text-slate-400 text-sm italic">Powered by Amplify AI Engine v2026</p>
    </div>
  );
};

export default App;



//1. Ref Management: Added useEffect with a pollIntervalRef cleanup. This prevents "memory leaks" where the app keeps trying to poll the server even if you close the tab or change the page.

//2. UI/UX Polish: Used a more modern Indigo/Slate color palette with Tailwind shadows and rounded corners (rounded-2xl).

//3. State Logic: Ensured that once uploading starts, the file input is disabled to prevent accidental double-submits.

//4. Error Handling: Added better visual distinction for error states and made messages more user-friendly.
