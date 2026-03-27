/**
 * FirmwareInfoPanel - Firmware version, motor enable/disable, buzzer test.
 */

import { useState, useEffect, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { useMotorControl } from '@/hooks/useMotorControl';
import { usePublisher } from '@/hooks/usePublisher';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import { Button } from '@/components/ui/button';
import { Cpu, Power, Volume2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function FirmwareInfoPanel() {
  const { ros, connectionState } = useRosContext();
  const { motorsEnabled, toggleMotors, isChanging } = useMotorControl();
  const publish = usePublisher<{ data: number }>({ topic: ROS_TOPICS.beep, messageType: ROS_MESSAGE_TYPES.uint16 });
  const [fwVersion, setFwVersion] = useState<string | null>(null);

  const isConnected = connectionState === 'connected';

  // Fetch firmware version on connect
  useEffect(() => {
    if (!ros || !isConnected) { setFwVersion(null); return; }

    const service = new ROSLIB.Service({
      ros,
      name: '/orbibot/get_firmware_version',
      serviceType: 'orbibot_msgs/srv/GetFirmwareVersion',
    });

    const request = new ROSLIB.ServiceRequest({});
    service.callService(request, (response: { version_string?: string; major?: number; minor?: number }) => {
      setFwVersion(response.version_string ?? `v${response.major ?? '?'}.${response.minor ?? '?'}`);
    }, () => {
      setFwVersion('N/A');
    });
  }, [ros, isConnected]);

  const handleBeep = useCallback(() => {
    publish({ data: 200 }); // 200ms beep
  }, [publish]);

  return (
    <div className="glass-panel p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Cpu className="w-4 h-4 text-primary" />
        Firmware
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Version</span>
          <span className="font-mono font-medium">{fwVersion ?? (isConnected ? 'Loading...' : 'Offline')}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Motors</span>
          <Button
            variant={motorsEnabled ? 'default' : 'outline'}
            size="sm"
            onClick={toggleMotors}
            disabled={!isConnected || isChanging}
            className="gap-1.5 h-7"
          >
            <Power className="w-3.5 h-3.5" />
            {motorsEnabled ? 'Enabled' : 'Disabled'}
          </Button>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Buzzer Test</span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleBeep}
            disabled={!isConnected}
            className="gap-1.5 h-7"
          >
            <Volume2 className="w-3.5 h-3.5" />
            Beep
          </Button>
        </div>
      </div>
    </div>
  );
}
