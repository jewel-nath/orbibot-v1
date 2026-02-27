/**
 * WebRTCVideo - WebRTC video stream display component
 *
 * Displays low-latency video stream from robot camera using WebRTC
 * Compatible with aiortc-based backend server
 */

import { useEffect, useRef } from 'react';
import { useWebRTCContext } from '@/contexts/WebRTCContext';
import { Video, VideoOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WebRTCVideoProps {
  className?: string;
  showLabel?: boolean;
  label?: string;
  objectFit?: 'cover' | 'contain';
}

export function CameraFeed({ className, showLabel = true, label = 'ORBIBOT CAM', objectFit = 'cover' }: WebRTCVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { stream, connectionState, error } = useWebRTCContext();

  // Attach stream to video element when available
  useEffect(() => {
    if (videoRef.current && stream) {
      console.log('[WebRTCVideo] Attaching stream to video element', {
        streamId: stream.id,
        videoTracks: stream.getVideoTracks().length,
        audioTracks: stream.getAudioTracks().length,
        videoTrackActive: stream.getVideoTracks()[0]?.enabled,
      });
      videoRef.current.srcObject = stream;

      // Ensure video plays (in case autoPlay fails)
      videoRef.current.play().catch((err) => {
        console.warn('[WebRTCVideo] Failed to auto-play video:', err);
      });
    }
  }, [stream]);

  const isConnected = connectionState === 'connected' && stream !== null;
  const isConnecting =
    connectionState === 'connecting' || connectionState === 'reconnecting';

  return (
    <div
      className={cn(
        'relative w-full h-full overflow-hidden',
        className
      )}
    >
      {/* Video Element */}
      {stream && (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={cn(
            'absolute inset-0 w-full h-full transition-opacity duration-300',
            objectFit === 'contain' ? 'object-contain' : 'object-cover',
            isConnected ? 'opacity-100' : 'opacity-0'
          )}
        />
      )}

      {/* Placeholder when disconnected or connecting */}
      {!isConnected && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-muted/20">
          <div className="text-muted-foreground">
            {isConnecting ? (
              <Video className="w-8 h-8 mb-2 animate-pulse" />
            ) : (
              <VideoOff className="w-8 h-8 mb-2" />
            )}
          </div>

          {isConnecting && (
            <>
              <p className="text-muted-foreground text-sm font-medium tracking-wide">
                CONNECTING TO VIDEO
              </p>
              <p className="text-muted-foreground/70 text-xs mt-1 uppercase">
                {connectionState}
              </p>
            </>
          )}

          {connectionState === 'disconnected' && (
            <div className="group text-center">
              <p className="text-muted-foreground text-sm font-medium tracking-wide">
                CAMERA OFFLINE
              </p>
              <div className="absolute left-1/2 -translate-x-1/2 mt-1 w-max max-w-[240px] bg-popover text-popover-foreground text-[10px] px-2 py-1 rounded shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 font-mono">
                ros2 launch orbibot_sensors camera.launch.py
              </div>
            </div>
          )}

          {connectionState === 'error' && (
            <>
              <p className="text-destructive text-sm font-medium tracking-wide">
                VIDEO CONNECTION ERROR
              </p>
              {error && (
                <p className="text-destructive/70 text-xs mt-1 max-w-xs text-center px-4">
                  {error.message}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {/* Status Indicator */}
      <div className="absolute top-1.5 left-1.5">
        <div className="flex items-center gap-1.5 bg-black/60 px-1.5 py-0.5 rounded backdrop-blur-sm">
          <div
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              isConnected && 'bg-green-500 animate-pulse',
              isConnecting && 'bg-yellow-500 animate-pulse',
              connectionState === 'error' && 'bg-red-500',
              connectionState === 'disconnected' && 'bg-muted'
            )}
          />
          <span className="text-[10px] font-mono text-white/90">
            {isConnected ? 'LIVE' : isConnecting ? 'CONNECTING' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* Camera Label */}
      {isConnected && showLabel && (
        <div className="absolute bottom-3 left-3 right-3 flex justify-between items-center text-xs font-mono">
          <div className="bg-background/80 px-2 py-1 rounded-sm border border-border backdrop-blur-sm">
            <span className="text-foreground">{label}</span>
          </div>
        </div>
      )}
    </div>
  );
}
