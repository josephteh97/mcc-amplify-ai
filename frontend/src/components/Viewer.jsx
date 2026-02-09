import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stage, useGLTF, Environment } from '@react-three/drei';
import { Loader } from 'lucide-react';

const Model = ({ url }) => {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
};

const Viewer = ({ modelUrl, imageUrl }) => {
  if (!modelUrl && !imageUrl) {
    return (
      <div className="w-full h-full bg-slate-900 flex items-center justify-center text-slate-500">
        <div className="text-center">
          <p className="text-xl font-light mb-2">No Model Loaded</p>
          <p className="text-sm opacity-60">Upload a floor plan to generate a 3D visualization</p>
        </div>
      </div>
    );
  }

  // If we have an image (rendering) but not a 3D model yet, or user prefers image
  if (imageUrl && !modelUrl) {
    return (
      <div className="w-full h-full bg-slate-900 flex items-center justify-center overflow-hidden">
        <img src={imageUrl} alt="Rendered View" className="max-w-full max-h-full object-contain shadow-2xl" />
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-slate-900 relative">
      <Canvas shadows dpr={[1, 2]} camera={{ fov: 50 }}>
        <Suspense fallback={null}>
          <Stage environment="city" intensity={0.6}>
            <Model url={modelUrl} />
          </Stage>
        </Suspense>
        <OrbitControls makeDefault />
        <Environment preset="city" />
      </Canvas>
      <div className="absolute top-4 right-4 bg-black/50 text-white px-3 py-1 rounded-full text-xs backdrop-blur-sm">
        Interactive 3D Mode
      </div>
    </div>
  );
};

export default Viewer;
