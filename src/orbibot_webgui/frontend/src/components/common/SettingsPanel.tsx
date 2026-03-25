/**
 * SettingsPanel - Configuration panel for WebSocket URL, topics, and limits
 */

import { useState } from 'react';
import { createPortal } from 'react-dom';
import { Settings, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSettings } from '@/contexts/SettingsContext';

interface SettingsPanelProps {
  className?: string;
}

export function SettingsPanel({ className }: SettingsPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { settings, updateSettings, resetSettings } = useSettings();

  return (
    <>
      {/* Settings Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={cn('p-2 rounded-lg hover:bg-muted/50 transition-colors', className)}
        aria-label="Open settings"
        title="Settings"
      >
        <Settings className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />
      </button>

      {/* Settings Panel Overlay — portaled to body to escape header stacking context */}
      {isOpen && createPortal(
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[60]"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel */}
          <div className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-card border-l border-border z-[70] overflow-y-auto shadow-2xl">
            {/* Header */}
            <div className="sticky top-0 bg-card border-b border-border px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-muted-foreground" />
                <h2 className="text-lg font-semibold">Settings</h2>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-lg hover:bg-muted/50 transition-colors"
                aria-label="Close settings"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Connection Settings */}
              <section>
                <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wide">
                  Connection
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">WebSocket URL</label>
                    <input
                      type="text"
                      value={settings.websocketUrl}
                      onChange={(e) => updateSettings({ websocketUrl: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="ws://localhost:9090"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      ROSBridge WebSocket server address (requires reload)
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">WebRTC Server</label>
                    <input
                      type="text"
                      value={settings.webrtcUrl}
                      onChange={(e) => updateSettings({ webrtcUrl: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="http://localhost:8081"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      WebRTC signaling server for camera streaming
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Chat API Server</label>
                    <input
                      type="text"
                      value={settings.chatApiUrl}
                      onChange={(e) => updateSettings({ chatApiUrl: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="http://localhost:8082"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      orbibot_agent chat_server HTTP API address
                    </p>
                  </div>
                </div>
              </section>

              {/* Control Limits */}
              <section>
                <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wide">
                  Control Limits
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Max Linear Velocity (m/s)
                    </label>
                    <input
                      type="number"
                      value={settings.maxLinearVelocity}
                      onChange={(e) => updateSettings({ maxLinearVelocity: parseFloat(e.target.value) })}
                      step="0.1"
                      min="0.1"
                      max="2.0"
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Max Angular Velocity (rad/s)
                    </label>
                    <input
                      type="number"
                      value={settings.maxAngularVelocity}
                      onChange={(e) => updateSettings({ maxAngularVelocity: parseFloat(e.target.value) })}
                      step="0.1"
                      min="0.1"
                      max="4.0"
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
              </section>

              {/* Topic Configuration */}
              <section>
                <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wide">
                  ROS Topics
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">LiDAR Scan</label>
                    <input
                      type="text"
                      value={settings.scanTopic}
                      onChange={(e) => updateSettings({ scanTopic: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="/scan"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Map</label>
                    <input
                      type="text"
                      value={settings.mapTopic}
                      onChange={(e) => updateSettings({ mapTopic: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="/map"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Odometry</label>
                    <input
                      type="text"
                      value={settings.odomTopic}
                      onChange={(e) => updateSettings({ odomTopic: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="/odom"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">IMU Data</label>
                    <input
                      type="text"
                      value={settings.imuTopic}
                      onChange={(e) => updateSettings({ imuTopic: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="/imu/data"
                    />
                  </div>
                </div>
              </section>

              {/* Reset Button */}
              <section className="pt-4 border-t border-border">
                <button
                  onClick={resetSettings}
                  className="w-full px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-lg transition-colors font-medium"
                >
                  Reset to Defaults
                </button>
                <p className="text-xs text-muted-foreground mt-2 text-center">
                  Reload the page to apply connection changes
                </p>
              </section>
            </div>
          </div>
        </>,
        document.body
      )}
    </>
  );
}
