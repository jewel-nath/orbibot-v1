import { Map } from 'lucide-react';
import { useState } from 'react';
import { MapView } from '@/components/visualization/MapView';
import { CameraFeed } from '@/features/video/CameraFeed';
import { LidarView } from '@/components/visualization/LidarView';
import { NavigationToolbar } from '@/components/navigation/NavigationToolbar';
import { useWebRTCContext } from '@/contexts/WebRTCContext';

export function UnifiedViewport() {
    const [cameraExpanded, setCameraExpanded] = useState(false);
    const [lidarExpanded, setLidarExpanded] = useState(false);
    const { connectionState, stream } = useWebRTCContext();

    const isCameraConnected = connectionState === 'connected' && stream !== null;
    const showCompactCamera = !isCameraConnected && !cameraExpanded;

    return (
        <div className="flex flex-col h-full border border-border rounded-lg bg-card overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/20">
                <div className="flex items-center gap-3">
                    <Map className="w-4 h-4 text-primary" />
                    <div className="flex items-center">
                        <NavigationToolbar />
                    </div>
                </div>
            </div>

            {/* Main Content Area - Map with overlays */}
            <div className="flex-1 relative bg-black/40 overflow-hidden">
                {/* Map View (always visible) */}
                <MapView />

                {/* Camera Overlay (top-left) */}
                <div
                    className={`absolute z-30 transition-all duration-200 ${cameraExpanded
                        ? 'top-3 left-3 w-[480px] h-[360px]'
                        : showCompactCamera
                            ? 'top-3 left-3 w-48 h-36'
                            : 'top-3 left-3 w-72 h-48'
                        }`}
                >
                    <div className="relative w-full h-full bg-black rounded-lg border border-white/10 overflow-hidden group cursor-pointer"
                        onClick={() => setCameraExpanded(!cameraExpanded)}
                    >
                        <CameraFeed className="w-full h-full" showLabel={false} />
                    </div>
                </div>

                {/* LiDAR Overlay (top-right, below header) */}
                <div
                    className={`absolute z-20 transition-all duration-200 ${lidarExpanded
                        ? 'top-3 right-3 w-72'
                        : 'top-3 right-3 w-48'
                        }`}
                >
                    <div className="cursor-pointer"
                        onClick={() => setLidarExpanded(!lidarExpanded)}
                    >
                        <LidarView
                            className="bg-black/80 backdrop-blur-md border-white/10 text-[10px]"
                            maxRange={5}
                            compact={!lidarExpanded}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
