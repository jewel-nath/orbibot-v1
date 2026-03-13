/**
 * Header - Top navigation bar with connection status, theme toggle, and settings
 */

import { ThemeToggle } from '@/components/common/ThemeToggle';
import { SettingsPanel } from '@/components/common/SettingsPanel';
import { ConnectionStatus } from '@/components/common/ConnectionStatus';
import { EmergencyStop } from '@/features/control/EmergencyStop';
import { HornButton } from '@/components/common/HornButton';
import { Car } from 'lucide-react';
import { useRosContext } from '@/contexts/RosContext';

export function Header() {
  const { connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';

  return (
    <header className="h-16 border-b border-border/40 bg-card/80 backdrop-blur-lg px-4 lg:px-6 flex items-center justify-between sticky top-0 z-50 shadow-sm">
      {/* Logo and Title */}
      <div className="flex items-center gap-3">
        <div className={`
          p-2 rounded-xl transition-all duration-300
          ${isConnected ? 'bg-primary/15 ring-1 ring-primary/20' : 'bg-muted/50'}
        `}>
          <Car className={`
            w-6 h-6 transition-colors duration-300
            ${isConnected ? 'text-primary' : 'text-muted-foreground'}
          `} strokeWidth={2} />
        </div>
        <div className="hidden sm:block">
          <h1 className="text-lg font-bold tracking-tight">OrbiBot Dashboard</h1>
        </div>
      </div>

      {/* Right Side: Connection Status, Emergency Stop and Controls */}
      <div className="flex items-center gap-2 lg:gap-4">
        <ConnectionStatus />
        
        <div className="flex items-center gap-1.5 border-l border-border pl-2 lg:pl-4">
          <HornButton />
          <EmergencyStop />
        </div>
        
        <div className="flex items-center gap-1.5 border-l border-border pl-2 lg:pl-4">
          <ThemeToggle />
          <SettingsPanel />
        </div>
      </div>
    </header>
  );
}