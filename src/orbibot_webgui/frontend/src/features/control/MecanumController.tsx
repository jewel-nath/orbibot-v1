import { useState, useCallback, useEffect, useRef } from 'react';
import { Gamepad2, Grid3X3 } from 'lucide-react';
import { DirectionButton } from './DirectionButton';
import { VirtualJoystick, RotationJoystick } from './VirtualJoystick';
import { useCmdVel } from '@/hooks/useCmdVel';
import { useRosContext } from '@/contexts/RosContext';
import { ROBOT_PARAMS, UI_CONSTANTS } from '@/lib/constants';
import { cn } from '@/lib/utils';

type ControlMode = 'buttons' | 'joystick';

interface MecanumControllerProps {
  className?: string;
}

/**
 * MecanumController - 11-button layout for mecanum wheel control
 *
 * Layout:
 * - 3x3 grid: 8 directional buttons + stop button
 * - 2 rotation buttons (CW/CCW) on the side
 * - Speed control integrated
 *
 * Movement mapping:
 * - ↑↓←→: Cardinal directions
 * - ↖↗↙↘: Diagonal movements
 * - ↻↺: Rotation (CW/CCW)
 * - ■: Emergency stop
 */
export function MecanumController({ className }: MecanumControllerProps) {
  const { connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';
  const { publishVelocity, stop } = useCmdVel();
  const [speedPercent, setSpeedPercent] = useState<number>(UI_CONSTANTS.defaultSpeedPercent);
  const [currentVelocity, setCurrentVelocity] = useState({ vx: 0, vy: 0, wz: 0 });
  const [controlMode, setControlMode] = useState<ControlMode>('buttons');

  // Joystick state for combining movement and rotation
  const joystickMoveRef = useRef({ x: 0, y: 0 });
  const joystickRotateRef = useRef(0);

  // Continuous publishing interval for buttons/keyboard
  const publishIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeVelocityRef = useRef({ vx: 0, vy: 0, wz: 0 });

  // Calculate scaled velocities based on speed percentage
  const maxLinear = ROBOT_PARAMS.defaultLinearVel;
  const maxAngular = ROBOT_PARAMS.defaultAngularVel;
  const speedScale = speedPercent / 100;

  const startPublishing = useCallback(
    (vx: number, vy: number, wz: number) => {
      activeVelocityRef.current = { vx, vy, wz };
      publishVelocity({ vx, vy, wz });
      setCurrentVelocity({ vx, vy, wz });

      // Clear any existing interval before starting a new one
      if (publishIntervalRef.current) {
        clearInterval(publishIntervalRef.current);
      }
      const intervalMs = Math.round(1000 / UI_CONSTANTS.publishRate);
      publishIntervalRef.current = setInterval(() => {
        publishVelocity(activeVelocityRef.current);
      }, intervalMs);
    },
    [publishVelocity]
  );

  const stopPublishing = useCallback(() => {
    if (publishIntervalRef.current) {
      clearInterval(publishIntervalRef.current);
      publishIntervalRef.current = null;
    }
    activeVelocityRef.current = { vx: 0, vy: 0, wz: 0 };
    stop();
    setCurrentVelocity({ vx: 0, vy: 0, wz: 0 });
  }, [stop]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (publishIntervalRef.current) {
        clearInterval(publishIntervalRef.current);
      }
    };
  }, []);

  const handlePress = useCallback(
    (vx: number, vy: number, wz: number) => {
      // Scale the normalized velocity (-1, 0, 1) by max velocities and speed percentage
      const scaledVx = vx * maxLinear * speedScale;
      const scaledVy = vy * maxLinear * speedScale;
      const scaledWz = wz * maxAngular * speedScale;

      startPublishing(scaledVx, scaledVy, scaledWz);
    },
    [startPublishing, maxLinear, maxAngular, speedScale]
  );

  const handleRelease = useCallback(() => {
    stopPublishing();
  }, [stopPublishing]);

  const handleEmergencyStop = useCallback(() => {
    stopPublishing();
  }, [stopPublishing]);

  // Joystick movement handler
  const handleJoystickMove = useCallback(
    (x: number, y: number) => {
      joystickMoveRef.current = { x, y };
      // Combine with current rotation
      const vx = y * maxLinear * speedScale;
      const vy = -x * maxLinear * speedScale;  // Joystick X-right = negative vy = robot right (ROS standard: positive=left)
      const wz = joystickRotateRef.current * maxAngular * speedScale;
      publishVelocity({ vx, vy, wz });
      setCurrentVelocity({ vx, vy, wz });
    },
    [publishVelocity, maxLinear, maxAngular, speedScale]
  );

  // Joystick rotation handler
  const handleJoystickRotate = useCallback(
    (w: number) => {
      joystickRotateRef.current = w;
      // Combine with current movement
      const vx = joystickMoveRef.current.y * maxLinear * speedScale;
      const vy = -joystickMoveRef.current.x * maxLinear * speedScale;
      const wz = w * maxAngular * speedScale;
      publishVelocity({ vx, vy, wz });
      setCurrentVelocity({ vx, vy, wz });
    },
    [publishVelocity, maxLinear, maxAngular, speedScale]
  );

  // Joystick release handlers
  const handleJoystickMoveRelease = useCallback(() => {
    joystickMoveRef.current = { x: 0, y: 0 };
    if (joystickRotateRef.current === 0) {
      stop();
      setCurrentVelocity({ vx: 0, vy: 0, wz: 0 });
    } else {
      const wz = joystickRotateRef.current * maxAngular * speedScale;
      publishVelocity({ vx: 0, vy: 0, wz });
      setCurrentVelocity({ vx: 0, vy: 0, wz });
    }
  }, [stop, publishVelocity, maxAngular, speedScale]);

  const handleJoystickRotateRelease = useCallback(() => {
    joystickRotateRef.current = 0;
    if (joystickMoveRef.current.x === 0 && joystickMoveRef.current.y === 0) {
      stop();
      setCurrentVelocity({ vx: 0, vy: 0, wz: 0 });
    } else {
      const vx = joystickMoveRef.current.y * maxLinear * speedScale;
      const vy = -joystickMoveRef.current.x * maxLinear * speedScale;
      publishVelocity({ vx, vy, wz: 0 });
      setCurrentVelocity({ vx, vy, wz: 0 });
    }
  }, [stop, publishVelocity, maxLinear, speedScale]);

  // Track which keys are currently pressed
  const pressedKeys = useRef<Set<string>>(new Set());

  // Keyboard shortcuts
  useEffect(() => {
    if (!isConnected) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input field
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      const key = e.key.toLowerCase();

      // Prevent multiple triggers for held keys
      if (pressedKeys.current.has(key)) return;
      pressedKeys.current.add(key);

      // Speed levels (1-9 = 10%-90%)
      if (key >= '1' && key <= '9') {
        const speed = parseInt(key) * 10;
        setSpeedPercent(speed);
        return;
      }

      // Emergency stop
      if (key === ' ' || key === 'escape') {
        e.preventDefault();
        handleEmergencyStop();
        return;
      }

      // Movement controls
      let vx = 0, vy = 0, wz = 0;

      switch (key) {
        // Forward/Backward
        case 'arrowup':
        case 'w':
          vx = 1;
          break;
        case 'arrowdown':
        case 's':
          vx = -1;
          break;

        // Strafe Left/Right
        case 'arrowleft':
        case 'a':
          vy = 1;
          break;
        case 'arrowright':
        case 'd':
          vy = -1;
          break;

        // Rotation
        case 'q':
          wz = 1; // CCW
          break;
        case 'e':
          wz = -1; // CW
          break;

        default:
          return;
      }

      e.preventDefault();
      handlePress(vx, vy, wz);
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      pressedKeys.current.delete(key);

      // Stop on key release (except for speed changes and emergency stop)
      if (key >= '1' && key <= '9') return;
      if (key === ' ' || key === 'escape') return;

      // Check if any movement keys are still pressed
      const movementKeys = ['arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'w', 'a', 's', 'd', 'q', 'e'];
      const anyMovementKeyPressed = movementKeys.some(k => pressedKeys.current.has(k));

      if (!anyMovementKeyPressed) {
        handleRelease();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      pressedKeys.current.clear();
    };
  }, [isConnected, handlePress, handleRelease, handleEmergencyStop, speedScale, maxLinear, maxAngular]);

  return (
    <div className={cn('flex flex-col gap-6 p-6 bg-card rounded-lg border', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Mecanum Controller</h2>
        {/* Control Mode Toggle */}
        <div className="flex rounded-lg border overflow-hidden">
          <button
            onClick={() => setControlMode('buttons')}
            className={cn(
              'px-2 py-1 transition-colors',
              controlMode === 'buttons'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted'
            )}
            title="Button mode"
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setControlMode('joystick')}
            className={cn(
              'px-2 py-1 transition-colors',
              controlMode === 'joystick'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted'
            )}
            title="Joystick mode (mobile)"
          >
            <Gamepad2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Controller Layout */}
      {controlMode === 'buttons' ? (
        <div className="flex gap-8 items-center justify-center">
          {/* Directional Pad (3x3 grid) */}
          <div className="flex flex-col gap-2">
            <div className="text-sm text-muted-foreground text-center mb-2">
              Directional Control
            </div>
            <div className="grid grid-cols-3 gap-2">
              {/* Row 1: NW, N, NE */}
              <DirectionButton
                symbol="↖"
                vx={1}
                vy={1}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />
              <DirectionButton
                symbol="↑"
                vx={1}
                vy={0}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />
              <DirectionButton
                symbol="↗"
                vx={1}
                vy={-1}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />

              {/* Row 2: W, STOP, E */}
              <DirectionButton
                symbol="←"
                vx={0}
                vy={1}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />
              <DirectionButton
                symbol="■"
                vx={0}
                vy={0}
                wz={0}
                onPress={handleEmergencyStop}
                onRelease={handleRelease}
                disabled={!isConnected}
                className="bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400 hover:bg-red-500/20"
              />
              <DirectionButton
                symbol="→"
                vx={0}
                vy={-1}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />

              {/* Row 3: SW, S, SE */}
              <DirectionButton
                symbol="↙"
                vx={-1}
                vy={1}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />
              <DirectionButton
                symbol="↓"
                vx={-1}
                vy={0}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />
              <DirectionButton
                symbol="↘"
                vx={-1}
                vy={-1}
                wz={0}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
              />
            </div>
          </div>

          {/* Rotation Control */}
          <div className="flex flex-col gap-2">
            <div className="text-sm text-muted-foreground text-center mb-2">
              Rotation
            </div>
            <div className="flex flex-col gap-2">
              <DirectionButton
                symbol="↻"
                vx={0}
                vy={0}
                wz={-1}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
                className="w-20 h-20"
              />
              <div className="text-xs text-center text-muted-foreground">CW</div>
              <DirectionButton
                symbol="↺"
                vx={0}
                vy={0}
                wz={1}
                onPress={handlePress}
                onRelease={handleRelease}
                disabled={!isConnected}
                className="w-20 h-20"
              />
              <div className="text-xs text-center text-muted-foreground">CCW</div>
            </div>
          </div>
        </div>
      ) : (
        /* Joystick Mode */
        <div className="flex gap-8 items-center justify-center">
          <VirtualJoystick
            onMove={handleJoystickMove}
            onRelease={handleJoystickMoveRelease}
            disabled={!isConnected}
            size={140}
            label="Movement"
          />
          <RotationJoystick
            onRotate={handleJoystickRotate}
            onRelease={handleJoystickRotateRelease}
            disabled={!isConnected}
            size={100}
          />
        </div>
      )}

      {/* Speed Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <label htmlFor="speed-slider" className="font-medium">
            Speed Level
          </label>
          <span className="text-muted-foreground">{speedPercent}%</span>
        </div>
        <input
          id="speed-slider"
          type="range"
          min={UI_CONSTANTS.minSpeedPercent}
          max={UI_CONSTANTS.maxSpeedPercent}
          value={speedPercent}
          onChange={(e) => setSpeedPercent(Number(e.target.value))}
          disabled={!isConnected}
          className="w-full h-2 bg-primary/20 rounded-lg appearance-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>10%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Current Velocity Display */}
      <div className="pt-4 border-t">
        <div className="text-sm text-muted-foreground mb-2">Current Velocity</div>
        <div className="grid grid-cols-3 gap-4 text-sm font-mono">
          <div>
            <span className="text-muted-foreground">Vx:</span>{' '}
            <span className={cn(currentVelocity.vx !== 0 && 'text-primary font-semibold')}>
              {currentVelocity.vx.toFixed(2)} m/s
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Vy:</span>{' '}
            <span className={cn(currentVelocity.vy !== 0 && 'text-primary font-semibold')}>
              {currentVelocity.vy.toFixed(2)} m/s
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Wz:</span>{' '}
            <span className={cn(currentVelocity.wz !== 0 && 'text-primary font-semibold')}>
              {currentVelocity.wz.toFixed(2)} rad/s
            </span>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Help */}
      <div className="pt-4 border-t">
        <div className="flex items-center justify-between text-sm text-muted-foreground mb-2">
          <span>Keyboard Shortcuts</span>
          <span className="text-xs">Press <kbd className="px-1.5 py-0.5 bg-muted rounded">?</kbd> for all shortcuts</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="space-y-1">
            <div><kbd className="px-2 py-1 bg-muted rounded">↑↓←→</kbd> or <kbd className="px-2 py-1 bg-muted rounded">WASD</kbd> Move</div>
            <div><kbd className="px-2 py-1 bg-muted rounded">Q</kbd> / <kbd className="px-2 py-1 bg-muted rounded">E</kbd> Rotate CCW/CW</div>
          </div>
          <div className="space-y-1">
            <div><kbd className="px-2 py-1 bg-muted rounded">Space</kbd> / <kbd className="px-2 py-1 bg-muted rounded">Esc</kbd> Stop</div>
            <div><kbd className="px-2 py-1 bg-muted rounded">1-9</kbd> Speed 10-90%</div>
          </div>
        </div>
      </div>
    </div>
  );
}
