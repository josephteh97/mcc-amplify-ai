import React, { useState } from 'react';
import UploadPanel from './UploadPanel';
import ChatPanel from './ChatPanel';
import Viewer from './Viewer';

const Layout = () => {
  const [modelUrl, setModelUrl] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);

  const handleJobCreated = (jobId) => {
    console.log("Job created:", jobId);
  };

  const handleProcessingComplete = (jobId, result) => {
    console.log("Processing complete:", result);
    // Assuming backend returns paths like /api/download/gltf/{jobId}
    if (result.files?.gltf) {
        setModelUrl(`/api/download/gltf/${jobId}`);
    }
    // If we have a render image
    if (result.files?.render) {
        setImageUrl(`/api/download/render/${jobId}`);
    } else {
        // Fallback or handle standard generation which might output gltf
        setModelUrl(`/api/download/gltf/${jobId}`);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-slate-100 overflow-hidden">
      {/* Sidebar */}
      <div className="w-[400px] flex flex-col gap-4 p-4 border-r border-gray-200 bg-white h-full z-10 shadow-xl shrink-0">
        <div className="h-auto">
          <UploadPanel 
            onJobCreated={handleJobCreated} 
            onProcessingComplete={handleProcessingComplete} 
          />
        </div>
        <div className="flex-1 min-h-0">
          <ChatPanel />
        </div>
      </div>

      {/* Main Viewer Area */}
      <div className="flex-1 h-full relative bg-slate-900">
        <Viewer modelUrl={modelUrl} imageUrl={imageUrl} />
      </div>
    </div>
  );
};

export default Layout;
