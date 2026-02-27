import { useCallback, useState } from 'react';
import { useCmdVel } from '@/hooks/useCmdVel';
import { useMotorControl } from '@/hooks/useMotorControl';
import { useRos } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';
import { Power, PowerOff } from 'lucide-react';

interface EmergencyStopProps {
  onStop?: () => void;
  className?: string;
}

/**
 * EmergencyStop - Motor enable/disable control via service
 *
 * Features:
 * - Uses /orbibot/set_motor_enable service to disable/enable motors
 * - Shows STOP button when motors enabled (red)
 * - Shows ENABLE button when motors disabled (blue)
 * - Compact navbar button only (no full mode)
 * - Also stops velocity commands when disabling
 */
export function EmergencyStop({ onStop, className }: EmergencyStopProps) {
  const { isConnected } = useRos();
  const { stop } = useCmdVel();
  const { motorsEnabled, isChanging, enableMotors, disableMotors, serviceAvailable } = useMotorControl();
  const [isActivated, setIsActivated] = useState(false);

  const handleStop = useCallback(() => {
    stop(); // Stop velocity commands
    disableMotors(); // Disable motors via service
    setIsActivated(true);
    onStop?.();

    // Reset visual feedback after 300ms
    setTimeout(() => {
      setIsActivated(false);
    }, 300);
  }, [stop, disableMotors, onStop]);

  const handleEnable = useCallback(() => {
    enableMotors();
  }, [enableMotors]);

  // Show STOP button when motors are enabled (or hardware unavailable)
  if (motorsEnabled || !serviceAvailable) {
    return (
      <button
        onClick={handleStop}
        disabled={!isConnected || isChanging || !serviceAvailable}
        className={cn(
          'relative flex items-center justify-center gap-1.5',
          'h-8 px-3 rounded-lg',
          'text-xs font-semibold',
          'transition-all duration-150',
          'select-none',
          // Normal state
          'bg-red-600 text-white',
          'hover:bg-red-700 active:scale-95',
          'border border-red-700',
          'shadow-sm hover:shadow-md',
          // Activated state
          isActivated && 'scale-95 bg-red-800 shadow-inner',
          // Disabled state
          (!isConnected || isChanging || !serviceAvailable) && 'opacity-40 cursor-not-allowed',
          className
        )}
        aria-label="Emergency Stop"
        title={!serviceAvailable ? 'Hardware not running. Launch robot hardware first.' : 'Disable motors (Emergency Stop)'}
      >
        <PowerOff className="w-4 h-4" />
        <span>{isChanging ? 'STOPPING...' : 'STOP'}</span>
      </button>
    );
  }

  // Show ENABLE button when motors are disabled
  return (
    <button
      onClick={handleEnable}
      disabled={!isConnected || isChanging || !serviceAvailable}
      className={cn(
        'relative flex items-center justify-center gap-1.5',
        'h-8 px-3 rounded-lg',
        'text-xs font-semibold',
        'transition-all duration-150',
        'select-none',
        // Normal state - blue theme to match dashboard
        'bg-primary text-white',
        'hover:bg-primary/90 active:scale-95',
        'border border-primary',
        'shadow-sm hover:shadow-md',
        // Disabled state
        (!isConnected || isChanging || !serviceAvailable) && 'opacity-40 cursor-not-allowed',
        className
      )}
      aria-label="Enable Motors"
      title={!serviceAvailable ? 'Hardware not running. Launch robot hardware first.' : 'Enable motors'}
    >
      <Power className="w-4 h-4" />
      <span>{isChanging ? 'ENABLING...' : 'ENABLE'}</span>
    </button>
  );
}
