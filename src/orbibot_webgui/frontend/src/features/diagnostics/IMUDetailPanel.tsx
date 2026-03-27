/**
 * IMUDetailPanel - Enhanced IMU visualization with gyro/accel time-series and bias tracking.
 */

import { useIMU } from '@/hooks/useIMU';
import { useRawIMU } from '@/hooks/useRawIMU';
import { useMultiChannelTimeSeries } from '@/hooks/useMultiChannelTimeSeries';
import { TimeSeriesChart } from './charts/TimeSeriesChart';
import { DiagnosticsSection } from './DiagnosticsSection';
import { AttitudeIndicator } from '@/features/telemetry/components/AttitudeIndicator';
import { CompassRose } from '@/features/telemetry/components/CompassRose';
import { Compass, Activity } from 'lucide-react';
import { useMemo } from 'react';

export function IMUDetailPanel() {
  const imu = useIMU();
  const rawImu = useRawIMU();

  // Gyro and accel channels for time-series
  const gyroValues: Record<string, number | null> = {
    'Wx': rawImu?.gyro?.x ?? null,
    'Wy': rawImu?.gyro?.y ?? null,
    'Wz': rawImu?.gyro?.z ?? null,
  };
  const accelValues: Record<string, number | null> = {
    'Ax': rawImu?.accel?.x ?? null,
    'Ay': rawImu?.accel?.y ?? null,
    'Az': rawImu?.accel?.z ?? null,
  };

  const gyroHistory = useMultiChannelTimeSeries(gyroValues, { maxAge: 30, sampleInterval: 100 });
  const accelHistory = useMultiChannelTimeSeries(accelValues, { maxAge: 30, sampleInterval: 100 });

  // Compute gyro bias (running average)
  const gyroBias = useMemo(() => {
    const wxData = gyroHistory['Wx'] ?? [];
    const wyData = gyroHistory['Wy'] ?? [];
    const wzData = gyroHistory['Wz'] ?? [];
    if (wxData.length < 10) return null;

    const avg = (arr: { value: number }[]) =>
      arr.reduce((sum, p) => sum + p.value, 0) / arr.length;

    return {
      wx: avg(wxData) * (180 / Math.PI),
      wy: avg(wyData) * (180 / Math.PI),
      wz: avg(wzData) * (180 / Math.PI),
    };
  }, [gyroHistory]);

  return (
    <div className="space-y-4">
      {/* Attitude + orientation values */}
      <DiagnosticsSection title="Orientation" icon={Compass}>
        <div className="grid grid-cols-1 sm:grid-cols-[auto_auto_1fr] gap-4 items-center">
          <div className="flex justify-center">
            <AttitudeIndicator
              roll={imu?.roll ?? 0}
              pitch={imu?.pitch ?? 0}
              size={120}
            />
          </div>
          <div className="flex justify-center">
            <CompassRose heading={imu?.yaw ?? 0} size={120} />
          </div>
          <div className="space-y-2">
            <div className="grid grid-cols-3 gap-3 text-center">
              {[
                { label: 'Roll', value: imu?.roll, unit: '°' },
                { label: 'Pitch', value: imu?.pitch, unit: '°' },
                { label: 'Yaw', value: imu?.yaw, unit: '°' },
              ].map(({ label, value, unit }) => (
                <div key={label} className="glass-panel p-2">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</div>
                  <div className="font-mono text-sm font-bold">{value != null ? value.toFixed(1) : '—'}{unit}</div>
                </div>
              ))}
            </div>
            {imu?.angular_velocity && (
              <div className="grid grid-cols-3 gap-3 text-center">
                {[
                  { label: 'Wx', value: imu.angular_velocity.x },
                  { label: 'Wy', value: imu.angular_velocity.y },
                  { label: 'Wz', value: imu.angular_velocity.z },
                ].map(({ label, value }) => (
                  <div key={label} className="glass-panel p-2">
                    <div className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</div>
                    <div className="font-mono text-xs">{value?.toFixed(3) ?? '—'} rad/s</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DiagnosticsSection>

      {/* Gyroscope time-series */}
      <DiagnosticsSection
        title="Gyroscope"
        icon={Activity}
        action={
          gyroBias && (
            <span className="text-[10px] font-mono text-muted-foreground">
              Bias: X={gyroBias.wx.toFixed(2)} Y={gyroBias.wy.toFixed(2)} Z={gyroBias.wz.toFixed(2)} °/s
            </span>
          )
        }
      >
        <TimeSeriesChart
          channels={[
            { name: 'Wx', color: '#EF4444', data: gyroHistory['Wx'] ?? [] },
            { name: 'Wy', color: '#22C55E', data: gyroHistory['Wy'] ?? [] },
            { name: 'Wz', color: '#6DB4FF', data: gyroHistory['Wz'] ?? [] },
          ]}
          height={220}
          yLabel="rad/s"
          timeWindow={30}
        />
      </DiagnosticsSection>

      {/* Accelerometer time-series */}
      <DiagnosticsSection title="Accelerometer" icon={Activity}>
        <TimeSeriesChart
          channels={[
            { name: 'Ax', color: '#EF4444', data: accelHistory['Ax'] ?? [] },
            { name: 'Ay', color: '#22C55E', data: accelHistory['Ay'] ?? [] },
            { name: 'Az', color: '#6DB4FF', data: accelHistory['Az'] ?? [] },
          ]}
          height={220}
          yLabel="m/s²"
          timeWindow={30}
          thresholds={[
            { value: 9.81, color: '#F59E0B', label: 'g = 9.81' },
          ]}
        />
      </DiagnosticsSection>
    </div>
  );
}
