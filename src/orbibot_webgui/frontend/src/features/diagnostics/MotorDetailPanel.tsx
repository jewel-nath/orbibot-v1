/**
 * MotorDetailPanel - Per-motor analysis with encoder rates and commanded vs actual velocity.
 */

import { useEncoders } from '@/hooks/useEncoders';
import { useJointStates } from '@/hooks/useJointStates';
import { useCmdVelMonitor } from '@/hooks/useCmdVelMonitor';
import { useOdometry } from '@/hooks/useOdometry';
import { useMultiChannelTimeSeries } from '@/hooks/useMultiChannelTimeSeries';
import { TimeSeriesChart } from './charts/TimeSeriesChart';
import { DiagnosticsSection } from './DiagnosticsSection';
import { RobotSilhouette } from '@/features/telemetry/components/RobotSilhouette';
import { MOTOR_MAPPING } from '@/lib/constants';
import { Cog, Activity } from 'lucide-react';

const MOTOR_COLORS = ['#6DB4FF', '#22C55E', '#F59E0B', '#EF4444'];

export function MotorDetailPanel() {
  const encoders = useEncoders();
  const joints = useJointStates();
  const cmdVel = useCmdVelMonitor();
  const odom = useOdometry();

  // Build encoder velocity values for multi-channel chart
  const encoderVelocities: Record<string, number | null> = {};
  if (joints) {
    for (let i = 0; i < joints.length; i++) {
      encoderVelocities[joints[i].abbreviation] = joints[i].velocityRadS;
    }
  }

  const encoderHistory = useMultiChannelTimeSeries(encoderVelocities, { maxAge: 60, sampleInterval: 200 });

  // Commanded vs actual velocity
  const cmdVsActual: Record<string, number | null> = {
    'Cmd Vx': cmdVel?.vx ?? null,
    'Actual Vx': odom?.vx ?? null,
    'Cmd Vy': cmdVel?.vy ?? null,
    'Actual Vy': odom?.vy ?? null,
  };
  const cmdVsActualHistory = useMultiChannelTimeSeries(cmdVsActual, { maxAge: 30, sampleInterval: 100 });

  // Build WheelData for silhouette
  const silhouetteWheels = MOTOR_MAPPING.map((motor, i) => ({
    id: motor.id,
    label: motor.abbreviation,
    encoderCount: encoders?.data?.[i] ?? 0,
    enabled: true,
  }));

  return (
    <div className="space-y-4">
      {/* Motor status cards + silhouette */}
      <DiagnosticsSection title="Motor Status" icon={Cog}>
        <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-4">
          <div className="flex items-center justify-center">
            <RobotSilhouette wheels={silhouetteWheels} width={160} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            {MOTOR_MAPPING.map((motor, i) => {
              const enc = encoders?.data?.[i] ?? 0;
              const vel = joints?.[i]?.velocityRadS ?? 0;
              const posRad = joints?.[i]?.positionRad ?? 0;

              return (
                <div key={motor.id} className="glass-panel p-3 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: MOTOR_COLORS[i] }}
                    />
                    <span className="text-sm font-semibold">{motor.name} — {motor.abbreviation}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                    <span className="text-muted-foreground">Encoder</span>
                    <span className="font-mono text-right">{enc.toLocaleString()}</span>
                    <span className="text-muted-foreground">Velocity</span>
                    <span className="font-mono text-right">{vel.toFixed(2)} rad/s</span>
                    <span className="text-muted-foreground">Position</span>
                    <span className="font-mono text-right">{posRad.toFixed(2)} rad</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </DiagnosticsSection>

      {/* Encoder rate time-series */}
      <DiagnosticsSection title="Wheel Velocities" icon={Activity}>
        <TimeSeriesChart
          channels={MOTOR_MAPPING.map((motor, i) => ({
            name: motor.abbreviation,
            color: MOTOR_COLORS[i],
            data: encoderHistory[motor.abbreviation] ?? [],
          }))}
          height={250}
          yLabel="rad/s"
          timeWindow={60}
        />
      </DiagnosticsSection>

      {/* Commanded vs actual */}
      <DiagnosticsSection title="Commanded vs Actual Velocity" icon={Activity}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <TimeSeriesChart
            channels={[
              { name: 'Cmd Vx', color: '#F59E0B', data: cmdVsActualHistory['Cmd Vx'] ?? [], dashed: true },
              { name: 'Actual Vx', color: '#6DB4FF', data: cmdVsActualHistory['Actual Vx'] ?? [] },
            ]}
            height={200}
            yLabel="m/s"
            timeWindow={30}
          />
          <TimeSeriesChart
            channels={[
              { name: 'Cmd Vy', color: '#F59E0B', data: cmdVsActualHistory['Cmd Vy'] ?? [], dashed: true },
              { name: 'Actual Vy', color: '#22C55E', data: cmdVsActualHistory['Actual Vy'] ?? [] },
            ]}
            height={200}
            yLabel="m/s"
            timeWindow={30}
          />
        </div>
      </DiagnosticsSection>
    </div>
  );
}
