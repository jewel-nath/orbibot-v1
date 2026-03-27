/**
 * IMUSection - Collapsible IMU attitude section.
 * Left: AttitudeIndicator SVG showing roll/pitch (yaw shown in CompassRose above).
 * Right: Roll / Pitch numeric values + total acceleration magnitude.
 * Collapsed by default — attitude is less critical for a ground robot.
 */

import { useIMU } from '@/hooks/useIMU';
import { useRos } from '@/contexts/RosContext';
import { SectionHeader, AttitudeIndicator } from './components';
import { Compass } from 'lucide-react';

interface IMUSectionProps {
  className?: string;
}

export function IMUSection({ className }: IMUSectionProps) {
  const { isConnected } = useRos();
  const imu = useIMU();

  const accelMag = imu?.linear_acceleration
    ? Math.sqrt(
        imu.linear_acceleration.x ** 2 +
        imu.linear_acceleration.y ** 2 +
        imu.linear_acceleration.z ** 2
      )
    : null;

  return (
    <SectionHeader
      icon={Compass}
      title="Attitude"
      defaultOpen={false}
      className={className}
    >
      {!isConnected || !imu ? (
        <div className="text-[10px] text-muted-foreground py-1">
          {!isConnected ? 'Offline' : 'Waiting for IMU…'}
        </div>
      ) : (
        <div className="flex items-start gap-3">
          <AttitudeIndicator roll={imu.roll} pitch={imu.pitch} size={80} />

          <div className="flex-1 min-w-0 space-y-1.5 pt-1">
            {[
              { label: 'Roll',  value: `${imu.roll.toFixed(1)}°` },
              { label: 'Pitch', value: `${imu.pitch.toFixed(1)}°` },
              { label: 'Yaw',   value: `${imu.yaw.toFixed(1)}°` },
              ...(accelMag !== null
                ? [{ label: '|a|', value: `${accelMag.toFixed(2)} m/s²` }]
                : []),
            ].map(({ label, value }) => (
              <div key={label} className="flex items-baseline justify-between gap-1">
                <span className="text-[10px] text-muted-foreground w-8 shrink-0">{label}</span>
                <span className="font-mono text-xs font-semibold">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </SectionHeader>
  );
}
