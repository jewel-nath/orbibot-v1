/**
 * DiagnosticsPage - Full-page diagnostics and tuning.
 * Sections (top to bottom): Connection/Telemetry, PID Tuning, PID Graph, Calibration.
 */

import { SafetyStatusWidget } from '@/features/telemetry/SafetyStatusWidget';
import { SystemInfo } from '@/features/telemetry/SystemInfo';
import { Encoders } from '@/features/telemetry/Encoders';
import { OdometryDisplay } from '@/features/telemetry/OdometryDisplay';
import { IMUWidget } from '@/features/telemetry/IMUWidget';
import { PIDTuningPanel } from '@/features/telemetry/PIDTuningPanel';
import { PIDResponseGraph } from '@/features/telemetry/PIDResponseGraph';
import { ImuCalibrationSection } from '@/features/telemetry/ImuCalibrationSection';
import { Wifi, Gauge, SlidersHorizontal, Compass } from 'lucide-react';
import { cn } from '@/lib/utils';

function Section({
  title,
  icon: Icon,
  children,
  className,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('rounded-xl border border-border bg-card/50 overflow-hidden', className)}>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/30">
        <Icon className="w-5 h-5 text-primary" />
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function DiagnosticsPage() {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 max-w-6xl mx-auto w-full px-2">
        {/* 1. Robot Status (connection in navbar; battery in System Health) */}
        <Section title="Robot Status" icon={Wifi}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <SafetyStatusWidget />
            <SystemInfo compact />
            <Encoders />
            <OdometryDisplay />
            <IMUWidget />
          </div>
        </Section>

        {/* 2. PID Tuning */}
        <Section title="PID Tuning" icon={SlidersHorizontal}>
          <PIDTuningPanel className="border-0 shadow-none bg-transparent" defaultExpanded />
        </Section>

        {/* 3. PID Response Graph */}
        <Section title="PID Response Graph" icon={Gauge}>
          <PIDResponseGraph />
        </Section>

        {/* 4. Calibration */}
        <Section title="Calibration" icon={Compass}>
          <ImuCalibrationSection />
        </Section>
      </div>
    </div>
  );
}
