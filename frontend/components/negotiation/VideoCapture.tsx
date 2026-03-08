import React, { useEffect, useRef } from 'react';
import { Camera, CameraOff, Video } from 'lucide-react';

interface VideoCaptureProps {
  isActive: boolean;
  onToggle: () => void;
}

export function VideoCapture({ isActive, onToggle }: VideoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    let active = true;

    async function setupCamera() {
      if (isActive) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
            audio: false
          });

          if (!active) {
            stream.getTracks().forEach(t => t.stop());
            return;
          }

          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        } catch (err) {
          console.error("Error accessing camera:", err);
        }
      } else {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
      }
    }

    setupCamera();

    return () => {
      active = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    };
  }, [isActive]);

  return (
    <div className="relative w-full aspect-video bg-neutral-900 rounded-xl overflow-hidden shadow-lg border border-neutral-800 flex flex-col group transition-all">
      {/* Container for the video stream (placeholder) */}
      <div className="flex-1 flex items-center justify-center relative">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`absolute inset-0 w-full h-full object-cover ${isActive ? 'opacity-100' : 'opacity-0'}`}
        />

        {!isActive && (
          <div className="flex flex-col items-center justify-center text-neutral-500 space-y-2 z-10 w-full h-full absolute inset-0 bg-neutral-900">
            <CameraOff className="w-12 h-12 opacity-50" />
            <p className="text-sm font-medium">Camera Inactive</p>
          </div>
        )}

        {isActive && (
          <div className="absolute top-4 left-4 flex flex-col items-center text-neutral-400 z-10">
            <span className="relative flex h-3 w-3 mb-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-full w-full bg-red-500"></span>
            </span>
          </div>
        )}
      </div>

      {/* Overlay controls - visible on hover or active state */}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-4 z-20">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-white/90">
            <Video className="w-4 h-4" />
            <span className="text-xs font-semibold">{isActive ? "User Feed (Live)" : "User Feed (Paused)"}</span>
          </div>
          <button
            onClick={onToggle}
            className={`p-2 rounded-full backdrop-blur-md transition-colors ${isActive
                ? 'bg-rose-500/20 text-rose-500 hover:bg-rose-500/30'
                : 'bg-white/10 text-white hover:bg-white/20'
              }`}
            title={isActive ? "Turn off camera" : "Turn on camera"}
          >
            {isActive ? <CameraOff className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
