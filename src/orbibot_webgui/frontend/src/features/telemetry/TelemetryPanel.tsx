/**
 * TelemetryPanel - Left panel telemetry container.
 * Orchestrates all monitoring sections in a unified scrollable column.
 * Replaces the previous: SafetyStatusWidget + SystemInfo + Encoders + OdometryDisplay + IMUWidget.
 *
 * Section order (top → bottom):
 *   1. RobotStatusHeader  — battery gauge + safety badges (always visible, no collapse)
 *   2. SystemResourcesSection — CPU/RAM/Temp/Disk bars + sparklines (open)
 *   3. PositionSection    — compass rose + X/Y/θ/dist (open)
 *   4. VelocitySection    — direction arrow + Vx/Vy/Wz + speed sparkline (open)
 *   5. WheelsSection      — robot silhouette + encoder counts (closed)
 *   6. IMUSection         — attitude indicator + roll/pitch/yaw (closed)
 */

import { cn } from '@/lib/utils';
import { RobotStatusHeader } from './RobotStatusHeader';
import { SystemResourcesSection } from './SystemResourcesSection';
import { PositionSection } from './PositionSection';
import { VelocitySection } from './VelocitySection';
import { WheelsSection } from './WheelsSection';
import { IMUSection } from './IMUSection';

interface TelemetryPanelProps {
  className?: string;
}

export function TelemetryPanel({ className }: TelemetryPanelProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <RobotStatusHeader />
      <SystemResourcesSection />
      <PositionSection />
      <VelocitySection />
      <WheelsSection />
      <IMUSection />
    </div>
  );
}
