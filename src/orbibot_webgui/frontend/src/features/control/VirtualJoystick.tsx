/**
 * VirtualJoystick - Touch-based joystick for mobile robot control
 *
 * Features:
 * - Circular touch area with visual feedback
 * - Smooth analog control output (-1 to 1)
 * - Deadzone for stability
 * - Auto-center on release
 * - Works alongside button controls on desktop
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface VirtualJoystickProps {
  onMove: (x: number, y: number) => void;
  onRelease: () => void;
  size?: number;
  deadzone?: number;
  disabled?: boolean;
  className?: string;
  label?: string;
}

export function VirtualJoystick({
  onMove,
  onRelease,
  size = 120,
  deadzone = 0.1,
  disabled = false,
  className,
  label = 'Movement',
}: VirtualJoystickProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isActive, setIsActive] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const centerRef = useRef({ x: 0, y: 0 });

  const maxDistance = size / 2 - 20; // Knob radius offset

  const handleStart = useCallback(
    (clientX: number, clientY: number) => {
      if (disabled || !containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      centerRef.current = {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
      };

      setIsActive(true);

      // Calculate initial position
      const dx = clientX - centerRef.current.x;
      const dy = clientY - centerRef.current.y;
      updatePosition(dx, dy);
    },
    [disabled]
  );

  const updatePosition = useCallback(
    (dx: number, dy: number) => {
      const distance = Math.sqrt(dx * dx + dy * dy);

      // Clamp to max distance
      let clampedX = dx;
      let clampedY = dy;
      if (distance > maxDistance) {
        clampedX = (dx / distance) * maxDistance;
        clampedY = (dy / distance) * maxDistance;
      }

      // Normalize to -1 to 1
      let normalizedX = clampedX / maxDistance;
      let normalizedY = -clampedY / maxDistance; // Invert Y

      // Apply deadzone
      const normalizedDistance = Math.sqrt(
        normalizedX * normalizedX + normalizedY * normalizedY
      );
      if (normalizedDistance < deadzone) {
        normalizedX = 0;
        normalizedY = 0;
      }

      setPosition({ x: clampedX, y: clampedY });
      onMove(normalizedX, normalizedY);
    },
    [maxDistance, deadzone, onMove]
  );

  const handleMove = useCallback(
    (clientX: number, clientY: number) => {
      if (!isActive) return;

      const dx = clientX - centerRef.current.x;
      const dy = clientY - centerRef.current.y;
      updatePosition(dx, dy);
    },
    [isActive, updatePosition]
  );

  const handleEnd = useCallback(() => {
    setIsActive(false);
    setPosition({ x: 0, y: 0 });
    onRelease();
  }, [onRelease]);

  // Touch event handlers
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleStart(touch.clientX, touch.clientY);
    },
    [handleStart]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleMove(touch.clientX, touch.clientY);
    },
    [handleMove]
  );

  // Mouse event handlers (for testing on desktop)
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      handleStart(e.clientX, e.clientY);
    },
    [handleStart]
  );

  useEffect(() => {
    if (!isActive) return;

    const handleGlobalMouseMove = (e: MouseEvent) => {
      handleMove(e.clientX, e.clientY);
    };

    const handleGlobalMouseUp = () => {
      handleEnd();
    };

    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove);
      window.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [isActive, handleMove, handleEnd]);

  return (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      {label && (
        <span className="text-xs text-muted-foreground">{label}</span>
      )}
      <div
        ref={containerRef}
        className={cn(
          'relative rounded-full border-2 select-none touch-none',
          'bg-muted/30',
          isActive ? 'border-primary' : 'border-primary/30',
          disabled && 'opacity-40 cursor-not-allowed'
        )}
        style={{ width: size, height: size }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleEnd}
        onTouchCancel={handleEnd}
        onMouseDown={handleMouseDown}
      >
        {/* Guide circles */}
        <div
          className="absolute rounded-full border border-dashed border-primary/20"
          style={{
            width: size * 0.66,
            height: size * 0.66,
            top: size * 0.17,
            left: size * 0.17,
          }}
        />

        {/* Center marker */}
        <div
          className="absolute w-2 h-2 bg-primary/30 rounded-full"
          style={{
            top: size / 2 - 4,
            left: size / 2 - 4,
          }}
        />

        {/* Knob */}
        <div
          className={cn(
            'absolute w-10 h-10 rounded-full',
            'bg-primary shadow-lg',
            'transition-shadow duration-150',
            isActive && 'shadow-primary/50 shadow-xl'
          )}
          style={{
            top: size / 2 - 20 + position.y,
            left: size / 2 - 20 + position.x,
          }}
        />
      </div>

      {/* Current values display */}
      {isActive && (
        <div className="flex gap-3 text-xs font-mono text-muted-foreground">
          <span>X: {(position.x / maxDistance).toFixed(2)}</span>
          <span>Y: {(-position.y / maxDistance).toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}

/**
 * RotationJoystick - Single-axis joystick for rotation control
 */
interface RotationJoystickProps {
  onRotate: (w: number) => void;
  onRelease: () => void;
  size?: number;
  disabled?: boolean;
  className?: string;
}

export function RotationJoystick({
  onRotate,
  onRelease,
  size = 80,
  disabled = false,
  className,
}: RotationJoystickProps) {
  const [rotation, setRotation] = useState(0);
  const [isActive, setIsActive] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const startAngleRef = useRef(0);
  const centerRef = useRef({ x: 0, y: 0 });

  const handleStart = useCallback(
    (clientX: number, clientY: number) => {
      if (disabled || !containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      centerRef.current = {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
      };

      const angle = Math.atan2(
        clientY - centerRef.current.y,
        clientX - centerRef.current.x
      );
      startAngleRef.current = angle;
      setIsActive(true);
    },
    [disabled]
  );

  const handleMove = useCallback(
    (clientX: number, clientY: number) => {
      if (!isActive) return;

      const angle = Math.atan2(
        clientY - centerRef.current.y,
        clientX - centerRef.current.x
      );

      let delta = angle - startAngleRef.current;

      // Normalize to -PI to PI
      while (delta > Math.PI) delta -= 2 * Math.PI;
      while (delta < -Math.PI) delta += 2 * Math.PI;

      // Clamp to -1 to 1
      const normalized = Math.max(-1, Math.min(1, delta / Math.PI));

      setRotation(normalized * 45); // Visual rotation in degrees
      onRotate(-normalized); // CCW is positive in ROS
    },
    [isActive, onRotate]
  );

  const handleEnd = useCallback(() => {
    setIsActive(false);
    setRotation(0);
    onRelease();
  }, [onRelease]);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleStart(touch.clientX, touch.clientY);
    },
    [handleStart]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleMove(touch.clientX, touch.clientY);
    },
    [handleMove]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      handleStart(e.clientX, e.clientY);
    },
    [handleStart]
  );

  useEffect(() => {
    if (!isActive) return;

    const handleGlobalMouseMove = (e: MouseEvent) => {
      handleMove(e.clientX, e.clientY);
    };

    const handleGlobalMouseUp = () => {
      handleEnd();
    };

    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove);
      window.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [isActive, handleMove, handleEnd]);

  return (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      <span className="text-xs text-muted-foreground">Rotation</span>
      <div
        ref={containerRef}
        className={cn(
          'relative rounded-full border-2 select-none touch-none',
          'bg-muted/30',
          isActive ? 'border-primary' : 'border-primary/30',
          disabled && 'opacity-40 cursor-not-allowed'
        )}
        style={{ width: size, height: size }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleEnd}
        onTouchCancel={handleEnd}
        onMouseDown={handleMouseDown}
      >
        {/* Rotation indicator */}
        <div
          className="absolute inset-2 rounded-full border-2 border-dashed border-primary/30 flex items-center justify-center"
          style={{ transform: `rotate(${rotation}deg)` }}
        >
          <div className="absolute top-0 w-2 h-4 bg-primary rounded-full" />
        </div>

        {/* Labels */}
        <div className="absolute top-1 left-1/2 -translate-x-1/2 text-[10px] text-muted-foreground">
          CCW
        </div>
        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[10px] text-muted-foreground">
          CW
        </div>
      </div>
    </div>
  );
}
