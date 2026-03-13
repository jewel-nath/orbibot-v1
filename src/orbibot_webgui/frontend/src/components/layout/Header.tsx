/**
 * Header - Top navigation bar with Dashboard/Diagnostics nav, connection status, theme toggle, and settings
 */

import { ThemeToggle } from '@/components/common/ThemeToggle';
import { SettingsPanel } from '@/components/common/SettingsPanel';
import { ConnectionStatus } from '@/components/common/ConnectionStatus';
import { EmergencyStop } from '@/features/control/EmergencyStop';
import { HornButton } from '@/components/common/HornButton';
import { Car, LayoutDashboard, Stethoscope } from 'lucide-react';
import { useRosContext } from '@/contexts/RosContext';
import { usePath } from '@/contexts/PathContext';
import { cn } from '@/lib/utils';

export function Header() {
  const { connectionState } = useRosContext();
  const { path, navigate } = usePath();
  const isConnected = connectionState === 'connected';

  return (
    <header className="h-16 border-b border-border/40 bg-card/80 backdrop-blur-lg px-4 lg:px-6 flex items-center justify-between sticky top-0 z-50 shadow-sm">
      {/* Logo, Title, and Nav */}
      <div className="flex items-center gap-4">
        <div className={`
          p-2 rounded-xl transition-all duration-300
          ${isConnected ? 'bg-primary/15 ring-1 ring-primary/20' : 'bg-muted/50'}
        `}>
          <Car className={`
            w-6 h-6 transition-colors duration-300
            ${isConnected ? 'text-primary' : 'text-muted-foreground'}
          `} strokeWidth={2} />
        </div>
        <div className="hidden sm:flex items-center gap-1">
          <h1 className="text-lg font-bold tracking-tight mr-2">OrbiBot</h1>
          <nav className="flex rounded-lg bg-muted/50 p-0.5">
            <button
              onClick={() => navigate('/')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                path === '/' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </button>
            <button
              onClick={() => navigate('/diagnostics')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                path === '/diagnostics' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Stethoscope className="w-4 h-4" />
              Diagnostics
            </button>
          </nav>
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