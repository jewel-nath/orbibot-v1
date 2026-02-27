import { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface DirectionButtonProps {
  symbol: string;           // ↑, ↓, ←, →, ↖, ↗, ↙, ↘, ↻, ↺, ■
  vx: number;               // -1, 0, or 1
  vy: number;               // -1, 0, or 1
  wz: number;               // -1, 0, or 1
  onPress: (vx: number, vy: number, wz: number) => void;
  onRelease: () => void;
  disabled?: boolean;
  className?: string;
}

export function DirectionButton({
  symbol,
  vx,
  vy,
  wz,
  onPress,
  onRelease,
  disabled = false,
  className
}: DirectionButtonProps) {
  const [isPressed, setIsPressed] = useState(false);

  const handleStart = useCallback(() => {
    if (disabled) return;
    setIsPressed(true);
    onPress(vx, vy, wz);
  }, [disabled, onPress, vx, vy, wz]);

  const handleEnd = useCallback(() => {
    if (disabled) return;
    setIsPressed(false);
    onRelease();
  }, [disabled, onRelease]);

  // Prevent default touch behavior to avoid scrolling
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    handleStart();
  }, [handleStart]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    handleEnd();
  }, [handleEnd]);

  return (
    <button
      onMouseDown={handleStart}
      onMouseUp={handleEnd}
      onMouseLeave={handleEnd}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleEnd}
      disabled={disabled}
      className={cn(
        'relative flex items-center justify-center',
        'w-16 h-16 rounded-lg',
        'text-2xl font-bold',
        'transition-all duration-150',
        'select-none touch-none',
        // Normal state
        'bg-primary/10 text-primary',
        'hover:bg-primary/20',
        'border-2 border-primary/30',
        // Pressed state
        isPressed && 'bg-primary text-primary-foreground scale-95 shadow-inner',
        // Disabled state
        disabled && 'opacity-40 cursor-not-allowed',
        className
      )}
      aria-label={`Move ${symbol}`}
      aria-pressed={isPressed}
    >
      {symbol}
    </button>
  );
}
