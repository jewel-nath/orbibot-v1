/**
 * App - Root application component
 */

import { useEffect } from 'react';
import { RosProvider } from '@/contexts/RosContext';
import { WebRTCProvider } from '@/contexts/WebRTCContext';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { SettingsProvider } from '@/contexts/SettingsContext';
import { Header } from '@/components/layout/Header';
import { Dashboard, DashboardLeft, DashboardCenter, DashboardRight } from '@/components/layout/Dashboard';
import { MobileJoystick } from '@/features/control/MobileJoystick';
import { SystemInfo } from '@/features/telemetry/SystemInfo';
import { SafetyStatusWidget } from '@/features/telemetry/SafetyStatusWidget';
import { Encoders } from '@/features/telemetry/Encoders';
import { OdometryDisplay } from '@/features/telemetry/OdometryDisplay';
import { IMUWidget } from '@/features/telemetry/IMUWidget';
import { UnifiedViewport } from '@/components/layout/UnifiedViewport';
import { MissionControl } from '@/components/layout/MissionControl';
import { ConnectionStatusBar } from '@/components/common/ConnectionStatusBar';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { KeyboardShortcutsDialog } from '@/components/common/KeyboardShortcutsDialog';
import { Toaster } from 'sonner';
import { ThemeProvider } from 'next-themes';

function App() {
  const showMobileController = window.location.pathname === '/controller';

  // Auto-redirect only devices with mobile User-Agent (phones/tablets), not narrow/touch desktop
  useEffect(() => {
    const preferDesktop = localStorage.getItem('preferDesktop') === 'true';
    const ua = typeof navigator !== 'undefined' ? navigator.userAgent.toLowerCase() : '';
    const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(ua);
    if (isMobileUA && !preferDesktop && !showMobileController) {
      window.location.pathname = '/controller';
    }
  }, [showMobileController]);

  return (
    <SettingsProvider>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        <RosProvider autoConnect={true}>
          <WebRTCProvider webrtcUrl={`http://${window.location.hostname}:8081`} autoConnect={true}>
            <NavigationProvider>
              
              {showMobileController ? (
                /* --- MOBILE CONTROLLER VIEW --- */
                <>
                  <MobileJoystick />
                  <Toaster position="top-center" />
                </>
              ) : (
                /* --- DESKTOP DASHBOARD VIEW --- */
                <>
                  <ConnectionStatusBar />
                  <div className="flex flex-col h-screen w-screen overflow-hidden">
                    <Header />
                    <ErrorBoundary>
                      <Dashboard>
                        {/* LEFT COLUMN: Compact Telemetry */}
                        <DashboardLeft>
                          <SafetyStatusWidget />
                          <SystemInfo compact />
                          <Encoders />
                          <OdometryDisplay />
                          <IMUWidget />
                        </DashboardLeft>

                        {/* CENTER COLUMN: Map with Camera + LiDAR overlays */}
                        <DashboardCenter>
                          <UnifiedViewport />
                        </DashboardCenter>

                        {/* RIGHT COLUMN: Mission Control */}
                        <DashboardRight>
                          <MissionControl />
                        </DashboardRight>
                      </Dashboard>
                    </ErrorBoundary>
                  </div>
                  <Toaster position="top-right" />
                  <KeyboardShortcutsDialog />
                </>
              )}

            </NavigationProvider>
          </WebRTCProvider>
        </RosProvider>
      </ThemeProvider>
    </SettingsProvider>
  );
}

export default App;