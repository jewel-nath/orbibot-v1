/**
 * NavigationToolbar - Floating toolbar for map interaction modes
 *
 * Features:
 * - Toggle buttons for interaction modes (Init Pose, Nav Goal, Waypoint)
 * - Cancel navigation button
 * - Keyboard shortcuts (I, G, W, Esc)
 * - Visual feedback for active mode and navigation status
 */

import { useEffect, useCallback } from 'react';
import { Crosshair, Flag, MapPin, X, Navigation } from 'lucide-react';
import { useNavigationContext } from '@/contexts/NavigationContext';
import { useRosContext } from '@/contexts/RosContext';
import { useNavGoal } from '@/hooks/useNavGoal';
import { cn } from '@/lib/utils';
import type { InteractionMode } from '@/types/interaction';

interface ToolbarButtonProps {
  icon: React.ReactNode;
  label: string;
  shortcut: string;
  active: boolean;
  disabled?: boolean;
  variant?: 'default' | 'destructive';
  onClick: () => void;
}

function ToolbarButton({
  icon,
  label,
  shortcut,
  active,
  disabled,
  variant = 'default',
  onClick,
}: ToolbarButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg',
        'text-sm font-medium transition-all duration-150',
        'select-none',
        // Default variant
        variant === 'default' && [
          'hover:bg-muted/80',
          active && 'bg-primary text-primary-foreground hover:bg-primary/90',
          !active && 'text-muted-foreground hover:text-foreground',
        ],
        // Destructive variant
        variant === 'destructive' && [
          'bg-red-600/90 text-white hover:bg-red-700',
          'shadow-sm',
        ],
        // Disabled state
        disabled && 'opacity-40 cursor-not-allowed pointer-events-none'
      )}
      title={`${label} (${shortcut})`}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
      <kbd className="hidden lg:inline-block ml-1 px-1.5 py-0.5 text-xs bg-black/20 rounded">
        {shortcut}
      </kbd>
    </button>
  );
}

interface NavigationToolbarProps {
  className?: string;
}

export function NavigationToolbar({ className }: NavigationToolbarProps) {
  const { connectionState } = useRosContext();
  const { mode, setMode, isNavigating, goalStatus, navigationAvailable, localizationAvailable } = useNavigationContext();
  const { cancelGoal } = useNavGoal();

  const isConnected = connectionState === 'connected';

  // Separate availability for each feature
  const canInitPose = isConnected && localizationAvailable;
  const canNavigate = isConnected && navigationAvailable;

  // Toggle mode handler
  const toggleMode = useCallback(
    (targetMode: InteractionMode) => {
      setMode(mode === targetMode ? 'none' : targetMode);
    },
    [mode, setMode]
  );

  // Handle cancel
  const handleCancel = useCallback(() => {
    cancelGoal();
    setMode('none');
  }, [cancelGoal, setMode]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Shift+W for waypoint mode (avoids conflict with W for movement)
      if (e.shiftKey && e.key.toLowerCase() === 'w') {
        e.preventDefault();
        toggleMode('waypoint');
        return;
      }

      // Don't process if any modifier is held (except for the above)
      if (e.ctrlKey || e.altKey || e.metaKey) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'i':
          toggleMode('init_pose');
          break;
        case 'g':
          toggleMode('nav_goal');
          break;
        case 'escape':
          handleCancel();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleMode, handleCancel]);

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-1 p-2',
        'bg-card/95 backdrop-blur-sm rounded-xl border shadow-lg',
        className
      )}
    >
      {/* Mode buttons */}
      <ToolbarButton
        icon={<Crosshair className="w-4 h-4" />}
        label="Init Pose"
        shortcut="I"
        active={mode === 'init_pose'}
        disabled={!canInitPose}
        onClick={() => toggleMode('init_pose')}
      />

      <ToolbarButton
        icon={<Flag className="w-4 h-4" />}
        label="Nav Goal"
        shortcut="G"
        active={mode === 'nav_goal'}
        disabled={!canNavigate}
        onClick={() => toggleMode('nav_goal')}
      />

      <ToolbarButton
        icon={<MapPin className="w-4 h-4" />}
        label="Waypoint"
        shortcut="⇧W"
        active={mode === 'waypoint'}
        disabled={!canNavigate}
        onClick={() => toggleMode('waypoint')}
      />

      {/* Separator */}
      <div className="w-px h-6 bg-border mx-1" />

      {/* Cancel button */}
      <ToolbarButton
        icon={<X className="w-4 h-4" />}
        label="Cancel"
        shortcut="Esc"
        active={false}
        disabled={!canNavigate || (!isNavigating && mode === 'none')}
        variant="destructive"
        onClick={handleCancel}
      />

      {/* Availability status dots */}
      <div className="flex items-center gap-1.5 ml-2 px-2 py-1 rounded-lg bg-muted/30">
        <span
          title={canInitPose ? 'AMCL: active' : 'AMCL: not running'}
          className={cn('w-2 h-2 rounded-full', canInitPose ? 'bg-green-500' : 'bg-muted-foreground/40')}
        />
        <span
          title={canNavigate ? 'Nav2: active' : 'Nav2: not running'}
          className={cn('w-2 h-2 rounded-full', canNavigate ? 'bg-blue-500' : 'bg-muted-foreground/40')}
        />
      </div>

      {/* Navigation status indicator */}
      {isNavigating && (
        <div className="flex items-center gap-2 ml-1 px-2 py-1 bg-blue-500/20 rounded-lg">
          <Navigation className="w-4 h-4 text-blue-500 animate-pulse" />
          <span className="text-xs text-blue-500 font-medium">Navigating</span>
        </div>
      )}

      {/* Goal status badge */}
      {goalStatus !== 'idle' && goalStatus !== 'navigating' && (
        <div
          className={cn(
            'ml-2 px-2 py-1 rounded-lg text-xs font-medium',
            goalStatus === 'succeeded' && 'bg-green-500/20 text-green-500',
            goalStatus === 'canceled' && 'bg-yellow-500/20 text-yellow-500',
            goalStatus === 'failed' && 'bg-red-500/20 text-red-500'
          )}
        >
          {goalStatus === 'succeeded' && 'Goal Reached'}
          {goalStatus === 'canceled' && 'Canceled'}
          {goalStatus === 'failed' && 'Failed'}
        </div>
      )}
    </div>
  );
}
