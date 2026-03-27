/**
 * DiagnosticsPage - Ultimate robot testing, data analysis, calibration & tuning.
 *
 * Tab-based layout with 6 tabs: Overview, Motors, Odometry, IMU, PID Tuning, Tools.
 * Each tab scrolls independently; unmounted tabs auto-unsubscribe from ROS topics.
 */

import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  LayoutDashboard,
  Cog,
  MapPin,
  Compass,
  SlidersHorizontal,
  Wrench,
} from 'lucide-react';

// Existing components (reused)
import { SafetyStatusWidget } from '@/features/telemetry/SafetyStatusWidget';
import { SystemInfo } from '@/features/telemetry/SystemInfo';
import { OdometryDisplay } from '@/features/telemetry/OdometryDisplay';
import { PIDTuningPanel } from '@/features/telemetry/PIDTuningPanel';
import { PIDResponseGraph } from '@/features/telemetry/PIDResponseGraph';
import { ImuCalibrationSection } from '@/features/telemetry/ImuCalibrationSection';

// New diagnostics components
import { DiagnosticsSection } from '@/features/diagnostics/DiagnosticsSection';
import { BatteryChart } from '@/features/diagnostics/BatteryChart';
import { FirmwareInfoPanel } from '@/features/diagnostics/FirmwareInfoPanel';
import { ConnectionHealthPanel } from '@/features/diagnostics/ConnectionHealthPanel';
import { MotorDetailPanel } from '@/features/diagnostics/MotorDetailPanel';
import { OdometryPathTrace } from '@/features/diagnostics/OdometryPathTrace';
import { OdometryComparisonChart } from '@/features/diagnostics/OdometryComparisonChart';
import { IMUDetailPanel } from '@/features/diagnostics/IMUDetailPanel';
import { MagnetometerPanel } from '@/features/diagnostics/MagnetometerPanel';
import { LidarDiagnosticsPanel } from '@/features/diagnostics/LidarDiagnosticsPanel';
import { DataExportPanel } from '@/features/diagnostics/DataExportPanel';
import { WheelCalibrationWizard } from '@/features/diagnostics/WheelCalibrationWizard';

import { cn } from '@/lib/utils';

const TABS = [
  { value: 'overview', label: 'Overview', icon: LayoutDashboard },
  { value: 'motors', label: 'Motors', icon: Cog },
  { value: 'odometry', label: 'Odometry', icon: MapPin },
  { value: 'imu', label: 'IMU', icon: Compass },
  { value: 'pid', label: 'PID Tuning', icon: SlidersHorizontal },
  { value: 'tools', label: 'Tools', icon: Wrench },
] as const;

export function DiagnosticsPage() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        {/* Sticky tab bar */}
        <div className="shrink-0 border-b border-border bg-background/80 backdrop-blur-sm px-4 pt-3 pb-0">
          <TabsList className="w-full justify-start gap-1 bg-transparent p-0 h-auto">
            {TABS.map(tab => (
              <TabsTrigger
                key={tab.value}
                value={tab.value}
                className={cn(
                  'gap-1.5 px-3 py-2 rounded-t-lg rounded-b-none border-b-2',
                  'data-[state=active]:border-primary data-[state=active]:bg-muted/50',
                  'data-[state=inactive]:border-transparent data-[state=inactive]:text-muted-foreground',
                )}
              >
                <tab.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {/* Tab content — each scrolls independently */}
        <div className="flex-1 overflow-hidden">
          {/* Overview */}
          <TabsContent value="overview" className="h-full overflow-y-auto p-4 lg:p-6 m-0">
            <div className="space-y-4 max-w-6xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <SafetyStatusWidget />
                <FirmwareInfoPanel />
              </div>
              <SystemInfo />
              <DiagnosticsSection title="Battery Voltage" icon={LayoutDashboard}>
                <BatteryChart />
              </DiagnosticsSection>
              <DiagnosticsSection title="Connection Health" icon={LayoutDashboard}>
                <ConnectionHealthPanel />
              </DiagnosticsSection>
            </div>
          </TabsContent>

          {/* Motors */}
          <TabsContent value="motors" className="h-full overflow-y-auto p-4 lg:p-6 m-0">
            <div className="space-y-4 max-w-6xl mx-auto">
              <MotorDetailPanel />
            </div>
          </TabsContent>

          {/* Odometry */}
          <TabsContent value="odometry" className="h-full overflow-y-auto p-4 lg:p-6 m-0">
            <div className="space-y-4 max-w-6xl mx-auto">
              <OdometryDisplay />
              <DiagnosticsSection title="Path Trace" icon={MapPin}>
                <OdometryPathTrace />
              </DiagnosticsSection>
              <DiagnosticsSection title="Raw vs Filtered Comparison" icon={MapPin}>
                <OdometryComparisonChart />
              </DiagnosticsSection>
            </div>
          </TabsContent>

          {/* IMU */}
          <TabsContent value="imu" className="h-full overflow-y-auto p-4 lg:p-6 m-0">
            <div className="space-y-4 max-w-6xl mx-auto">
              <IMUDetailPanel />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <DiagnosticsSection title="Magnetometer" icon={Compass}>
                  <MagnetometerPanel />
                </DiagnosticsSection>
                <DiagnosticsSection title="IMU Calibration" icon={Compass}>
                  <ImuCalibrationSection />
                </DiagnosticsSection>
              </div>
            </div>
          </TabsContent>

          {/* PID Tuning */}
          <TabsContent value="pid" className="h-full overflow-y-auto p-4 lg:p-6 m-0">
            <div className="space-y-4 max-w-6xl mx-auto">
              <DiagnosticsSection title="PID Tuning" icon={SlidersHorizontal}>
                <PIDTuningPanel className="border-0 shadow-none bg-transparent" defaultExpanded />
              </DiagnosticsSection>
              <DiagnosticsSection title="PID Response Graph" icon={SlidersHorizontal}>
                <PIDResponseGraph />
              </DiagnosticsSection>
            </div>
          </TabsContent>

          {/* Tools */}
          <TabsContent value="tools" className="h-full overflow-y-auto p-4 lg:p-6 m-0">
            <div className="space-y-4 max-w-6xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <DiagnosticsSection title="LiDAR Scan" icon={Wrench}>
                  <LidarDiagnosticsPanel />
                </DiagnosticsSection>
                <DiagnosticsSection title="Data Export" icon={Wrench}>
                  <DataExportPanel />
                </DiagnosticsSection>
              </div>
              <DiagnosticsSection title="Wheel Calibration" icon={Wrench}>
                <WheelCalibrationWizard />
              </DiagnosticsSection>
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
