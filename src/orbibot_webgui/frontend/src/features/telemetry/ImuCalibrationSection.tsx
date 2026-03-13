/**
 * ImuCalibrationSection - Trigger magnetometer calibration via /orbibot/calibrate_imu.
 * Hard iron only (firmware/driver); no scatter or soft iron in UI.
 */

import { useState, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Compass, Loader2 } from 'lucide-react';

const DEFAULT_CALIBRATION_TIME = 10;

export function ImuCalibrationSection() {
  const { ros, connectionState } = useRosContext();
  const [calibrationTime, setCalibrationTime] = useState(DEFAULT_CALIBRATION_TIME);
  const [isCalibrating, setIsCalibrating] = useState(false);

  const handleCalibrate = useCallback(() => {
    if (!ros || connectionState !== 'connected') {
      toast.error('Not connected to ROS');
      return;
    }

    setIsCalibrating(true);
    const time = Math.max(1, Math.min(60, Math.round(calibrationTime)));

    const service = new ROSLIB.Service({
      ros,
      name: '/orbibot/calibrate_imu',
      serviceType: 'orbibot_msgs/srv/CalibrateIMU',
    });

    const request = new ROSLIB.ServiceRequest({
      calibration_time: time,
    });

    service.callService(
      request,
      (response: { success: boolean; message: string }) => {
        setIsCalibrating(false);
        if (response.success) {
          toast.success('Magnetometer calibration', { description: response.message });
        } else {
          toast.error('Calibration failed', { description: response.message });
        }
      },
      (error: string) => {
        setIsCalibrating(false);
        toast.error('Calibration request failed', { description: error });
      }
    );
  }, [ros, connectionState, calibrationTime]);

  const isConnected = connectionState === 'connected' && !!ros;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Run magnetometer (hard iron) calibration. Keep the robot still or rotate slowly during the
        calibration time. Results are applied on the robot; no scatter plot in this UI.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Calibration time (s):</span>
          <input
            type="number"
            min={1}
            max={60}
            value={calibrationTime}
            onChange={(e) => setCalibrationTime(parseInt(e.target.value, 10) || DEFAULT_CALIBRATION_TIME)}
            className="w-16 px-2 py-1 text-sm rounded border border-border bg-background"
          />
        </label>
        <Button
          onClick={handleCalibrate}
          disabled={!isConnected || isCalibrating}
          className="gap-2"
        >
          {isCalibrating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Compass className="w-4 h-4" />
          )}
          {isCalibrating ? 'Calibrating…' : 'Calibrate magnetometer'}
        </Button>
      </div>
      {!isConnected && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Connect to ROS and ensure the hardware node is running to calibrate.
        </p>
      )}
    </div>
  );
}
