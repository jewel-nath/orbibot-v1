
import { useState, useCallback, useRef, useEffect } from 'react';
import { useCmdVel } from '@/hooks/useCmdVel';
import { useRosContext } from '@/contexts/RosContext';
import { VirtualJoystick, RotationJoystick } from './VirtualJoystick';
import { EmergencyStop } from './EmergencyStop';
import { ROBOT_PARAMS } from '@/lib/constants';
import { Wifi, WifiOff, RotateCcw } from 'lucide-react';
import { CameraFeed } from '@/features/video/CameraFeed';
import { MapView } from '@/components/visualization/MapView';
import { cn } from '@/lib/utils';

type CenterView = 'camera' | 'map';

export function MobileJoystick() {
    const { connectionState } = useRosContext();
    const isConnected = connectionState === 'connected';
    const { publishVelocity, stop } = useCmdVel();
    const [speedPercent, setSpeedPercent] = useState<number>(50);
    const [isPortrait, setIsPortrait] = useState(
        typeof window !== 'undefined' && window.innerHeight > window.innerWidth
    );
    const [centerView, setCenterView] = useState<CenterView>('camera');

    // Ref to track current inputs
    const moveRef = useRef({ x: 0, y: 0 });
    const rotateRef = useRef(0);

    // Orientation lock effect
    useEffect(() => {
        // Try to lock orientation to landscape
        const orientation = screen.orientation as any;
        if (orientation?.lock) {
            orientation.lock('landscape').catch((err: Error) => {
                console.warn('Orientation lock not supported:', err);
            });
        }

        // Detect orientation changes
        const handleOrientationChange = () => {
            setIsPortrait(window.innerHeight > window.innerWidth);
        };

        window.addEventListener('resize', handleOrientationChange);

        return () => {
            window.removeEventListener('resize', handleOrientationChange);
            if (orientation?.unlock) {
                orientation.unlock();
            }
        };
    }, []);

    // Constants
    const maxLinear = ROBOT_PARAMS.defaultLinearVel;
    const maxAngular = ROBOT_PARAMS.defaultAngularVel;
    const speedScale = speedPercent / 100;

    // Unified update loop
    const updateVelocity = useCallback(() => {
        const vx = moveRef.current.y * maxLinear * speedScale;
        // Fix for inverted strafe: Positive Joystick X (Right) should produce positive vy (Right on this robot)
        const vy = moveRef.current.x * maxLinear * speedScale;
        const wz = rotateRef.current * maxAngular * speedScale;

        publishVelocity({ vx, vy, wz });
    }, [publishVelocity, maxLinear, maxAngular, speedScale]);

    const handleMove = useCallback((x: number, y: number) => {
        moveRef.current = { x, y };
        updateVelocity();
    }, [updateVelocity]);

    const handleRotate = useCallback((w: number) => {
        rotateRef.current = w;
        updateVelocity();
    }, [updateVelocity]);

    const handleRelease = useCallback(() => {
        // Only stop if both inputs are zero, but handleMove/Rotate might set them to 0 before this?
        // Actually VirtualJoystick calls onMove(0,0) before onRelease? 
        // Usually onRelease is enough.
        // If one is released but other is active, we should just update.
        // But VirtualJoystick resets on release.
        // Let's rely on the state refs which should be updated by onMove(0,0) before release/during release.
        // Actually VirtualJoystick calls onRelease, but we need to ensure the ref is 0.

        // Safety: just update.
        updateVelocity();
    }, [updateVelocity]);

    // Special handler for complete stop (e.g. emergency)
    const handleStop = useCallback(() => {
        moveRef.current = { x: 0, y: 0 };
        rotateRef.current = 0;
        stop();
    }, [stop]);

    // Adjust refs on release explicitly to be safe
    const handleMoveRelease = useCallback(() => {
        moveRef.current = { x: 0, y: 0 };
        handleRelease();
    }, [handleRelease]);

    const handleRotateRelease = useCallback(() => {
        rotateRef.current = 0;
        handleRelease();
    }, [handleRelease]);

    // Show overlay when in portrait mode
    if (isPortrait) {
        return (
            <div className="fixed inset-0 bg-background flex items-center justify-center p-6">
                <div className="text-center">
                    <RotateCcw className="w-16 h-16 mx-auto mb-4 text-primary animate-pulse" />
                    <p className="text-xl font-bold mb-2">Please rotate your device</p>
                    <p className="text-sm text-muted-foreground">Landscape mode required for mobile controller</p>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-background touch-none select-none flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b bg-card/50 backdrop-blur">
                <div className="flex items-center gap-2">
                    <h1 className="text-base font-bold tracking-tight">OrbiBot</h1>
                    {isConnected ? (
                        <div className="flex items-center gap-1 text-green-500 text-xs bg-green-500/10 px-1.5 py-0.5 rounded-full">
                            <Wifi className="w-3 h-3" />
                        </div>
                    ) : (
                        <div className="flex items-center gap-1 text-red-500 text-xs bg-red-500/10 px-1.5 py-0.5 rounded-full">
                            <WifiOff className="w-3 h-3" />
                        </div>
                    )}
                </div>

                {/* View toggle tabs */}
                <div className="flex items-center gap-1 bg-muted/30 rounded-lg p-0.5">
                    <button
                        onClick={() => setCenterView('camera')}
                        className={cn(
                            'px-2 py-1 rounded text-xs font-medium transition-colors',
                            centerView === 'camera'
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:text-foreground'
                        )}
                    >
                        Camera
                    </button>
                    <button
                        onClick={() => setCenterView('map')}
                        className={cn(
                            'px-2 py-1 rounded text-xs font-medium transition-colors',
                            centerView === 'map'
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:text-foreground'
                        )}
                    >
                        Map
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    {/* Emergency Stop */}
                    <EmergencyStop onStop={handleStop} className="scale-75" />
                    <div className="flex flex-col items-end min-w-[32px]">
                        <span className="text-[10px] text-muted-foreground leading-tight">Speed</span>
                        <span className="font-mono font-bold text-sm leading-tight">{speedPercent}%</span>
                    </div>
                    <input
                        type="range"
                        min="10"
                        max="100"
                        step="10"
                        value={speedPercent}
                        onChange={(e) => setSpeedPercent(Number(e.target.value))}
                        className="w-16 h-1.5 bg-primary/20 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                    />
                </div>
            </div>

            {/* Main Control Area */}
            <div className="flex-1 flex items-center justify-between px-4 pb-4 relative">

                {/* Left: Movement Joystick */}
                <div className="relative z-10">
                    <VirtualJoystick
                        onMove={handleMove}
                        onRelease={handleMoveRelease}
                        size={140}
                        disabled={!isConnected}
                        label="Translate"
                    />
                </div>

                {/* Center: Camera / Map */}
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-0 pointer-events-none">
                    {centerView === 'camera' && (
                        <div className="w-[280px] h-[210px] rounded-lg overflow-hidden border-2 border-primary shadow-xl pointer-events-auto">
                            <CameraFeed showLabel={false} objectFit="contain" />
                        </div>
                    )}

                    {centerView === 'map' && (
                        <div className="w-[280px] h-[210px] rounded-lg overflow-hidden border-2 border-primary shadow-xl pointer-events-auto">
                            <MapView />
                        </div>
                    )}
                </div>

                {/* Right: Rotation Joystick */}
                <div className="relative z-10">
                    <RotationJoystick
                        onRotate={handleRotate}
                        onRelease={handleRotateRelease}
                        size={120}
                        disabled={!isConnected}
                    />
                </div>
            </div>

            {/* Footer Instructions */}
            <div className="flex items-center justify-center text-[10px] text-muted-foreground px-3 py-1.5 border-t bg-card/30">
                <button
                    onClick={() => {
                        localStorage.setItem('preferDesktop', 'true');
                        window.location.pathname = '/';
                    }}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                >
                    Desktop Mode
                </button>
            </div>
        </div>
    );
}
