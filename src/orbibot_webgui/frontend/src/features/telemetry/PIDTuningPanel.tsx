/**
 * PIDTuningPanel - Single PID gain tuning interface
 *
 * Features:
 * - Single motor PID gains (optimized for mid-speed autonomous navigation)
 * - Yaw PID gains tab
 * - Slider controls with numeric input
 * - Apply sends gains to firmware, Save persists to flash
 * - Reset to defaults
 *
 * Topics Published:
 * - /orbibot/pid_params (Float32MultiArray) - [kp, ki, kd]
 * - /orbibot/yaw_pid_params (Float32MultiArray) - [kp, ki, kd]
 * - /orbibot/pid_save (Float32MultiArray) - [kp, ki, kd] triggers flash save
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  SlidersHorizontal,
  RotateCcw,
  Send,
  Save,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useRosContext } from '@/contexts/RosContext';
import { useMotorControl } from '@/hooks/useMotorControl';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { ROS_TOPICS } from '@/lib/constants';
import ROSLIB from 'roslib';

// Default single PID values (optimized for mid-speed autonomous navigation)
const DEFAULT_MOTOR_PID = { kp: 0.8, ki: 0.06, kd: 0.5 };
const DEFAULT_YAW_PID = { kp: 0.4, ki: 0.0, kd: 0.1 };

// PID parameter limits (firmware accepts 0-10)
const PID_MIN = 0;
const PID_MAX = 10;
const PID_STEP = 0.01;

interface PIDGains {
  kp: number;
  ki: number;
  kd: number;
}

interface PIDTuningPanelProps {
  className?: string;
}

function PIDSlider({
  label,
  value,
  onChange,
  min = PID_MIN,
  max = PID_MAX,
  step = PID_STEP,
  disabled = false,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-muted-foreground">{label}</label>
        <input
          type="number"
          value={value}
          onChange={(e) => {
            const val = parseFloat(e.target.value) || 0;
            onChange(Math.max(min, Math.min(max, val)));
          }}
          onBlur={(e) => {
            const val = parseFloat(e.target.value) || 0;
            const clamped = Math.max(min, Math.min(max, val));
            if (clamped !== value) {
              onChange(clamped);
            }
          }}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          className="w-16 px-2 py-0.5 text-xs text-right bg-muted border rounded focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        />
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-muted accent-primary disabled:opacity-50 disabled:cursor-not-allowed"
      />
    </div>
  );
}

export function PIDTuningPanel({ className }: PIDTuningPanelProps) {
  const { ros, connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';
  const { serviceAvailable: hardwareAvailable } = useMotorControl();

  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'motor' | 'yaw'>('motor');

  // Single PID state
  const [motorPID, setMotorPID] = useState<PIDGains>({ ...DEFAULT_MOTOR_PID });
  const [yawPID, setYawPID] = useState<PIDGains>({ ...DEFAULT_YAW_PID });

  // Publisher refs
  const pidPubRef = useRef<ROSLIB.Topic | null>(null);
  const savePubRef = useRef<ROSLIB.Topic | null>(null);
  const yawPubRef = useRef<ROSLIB.Topic | null>(null);

  // Setup publishers
  useEffect(() => {
    if (!ros || !isConnected) {
      pidPubRef.current = null;
      savePubRef.current = null;
      yawPubRef.current = null;
      return;
    }

    pidPubRef.current = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.pidParams,
      messageType: 'std_msgs/Float32MultiArray',
    });

    savePubRef.current = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.pidSave,
      messageType: 'std_msgs/Float32MultiArray',
    });

    yawPubRef.current = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.yawPidParams,
      messageType: 'std_msgs/Float32MultiArray',
    });

    return () => {
      pidPubRef.current = null;
      savePubRef.current = null;
      yawPubRef.current = null;
    };
  }, [ros, isConnected]);

  // Apply motor PID (sends to firmware RAM, not flash)
  const applyMotorPID = useCallback(() => {
    if (!pidPubRef.current) {
      toast.error('Not connected to ROS');
      return;
    }

    pidPubRef.current.publish(
      new ROSLIB.Message({ data: [motorPID.kp, motorPID.ki, motorPID.kd] })
    );

    toast.success('Motor PID applied', {
      description: `Kp=${motorPID.kp.toFixed(3)} Ki=${motorPID.ki.toFixed(3)} Kd=${motorPID.kd.toFixed(3)}`,
    });
  }, [motorPID]);

  // Save to flash
  const saveToFlash = useCallback(() => {
    if (!savePubRef.current) {
      toast.error('Not connected to ROS');
      return;
    }

    // First apply, then save
    applyMotorPID();

    savePubRef.current.publish(
      new ROSLIB.Message({ data: [motorPID.kp, motorPID.ki, motorPID.kd] })
    );

    toast.success('PID gains saved to flash', {
      description: 'Settings will persist across power cycles',
    });
  }, [motorPID, applyMotorPID]);

  // Apply yaw PID
  const applyYawPID = useCallback(() => {
    if (!yawPubRef.current) {
      toast.error('Not connected to ROS');
      return;
    }

    yawPubRef.current.publish(
      new ROSLIB.Message({ data: [yawPID.kp, yawPID.ki, yawPID.kd] })
    );

    toast.success('Yaw PID updated', {
      description: `Kp=${yawPID.kp.toFixed(2)} Ki=${yawPID.ki.toFixed(2)} Kd=${yawPID.kd.toFixed(2)}`,
    });
  }, [yawPID]);

  // Reset to defaults
  const resetMotorPID = useCallback(() => {
    setMotorPID({ ...DEFAULT_MOTOR_PID });
    toast.info('Motor PID reset to defaults');
  }, []);

  const resetYawPID = useCallback(() => {
    setYawPID({ ...DEFAULT_YAW_PID });
    toast.info('Yaw PID reset to defaults');
  }, []);

  return (
    <div
      className={cn(
        'bg-card rounded-lg border-2 border-blue-500/50 shadow-sm',
        className
      )}
    >
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-blue-500/10 transition-colors rounded-t-lg bg-blue-500/5"
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-blue-500" />
          <span className="font-medium text-sm">PID Tuning</span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-blue-500/70" />
        ) : (
          <ChevronRight className="w-4 h-4 text-blue-500/70" />
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-3 pt-0 space-y-3">
          {/* Tab Selection */}
          <div className="flex gap-1 p-1 bg-muted rounded-lg">
            <button
              onClick={() => setActiveTab('motor')}
              disabled={!hardwareAvailable}
              className={cn(
                'flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-colors',
                activeTab === 'motor'
                  ? 'bg-background shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              Motor PID
            </button>
            <button
              onClick={() => setActiveTab('yaw')}
              disabled={!hardwareAvailable}
              className={cn(
                'flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-colors',
                activeTab === 'yaw'
                  ? 'bg-background shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              Yaw PID
            </button>
          </div>

          {/* Motor PID — Single Level */}
          {activeTab === 'motor' && (
            <div className="space-y-3">
              <div className="p-2 bg-muted/30 rounded-md">
                <div className="text-xs font-semibold text-muted-foreground mb-2">
                  Single PID (Mid-Speed Optimized)
                </div>
                <PIDSlider
                  label="Kp (Proportional)"
                  value={motorPID.kp}
                  onChange={(v) => setMotorPID((prev) => ({ ...prev, kp: v }))}
                  disabled={!hardwareAvailable}
                />
                <PIDSlider
                  label="Ki (Integral)"
                  value={motorPID.ki}
                  onChange={(v) => setMotorPID((prev) => ({ ...prev, ki: v }))}
                  max={2}
                  disabled={!hardwareAvailable}
                />
                <PIDSlider
                  label="Kd (Derivative)"
                  value={motorPID.kd}
                  onChange={(v) => setMotorPID((prev) => ({ ...prev, kd: v }))}
                  max={5}
                  disabled={!hardwareAvailable}
                />
              </div>

              {/* Motor PID Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={resetMotorPID}
                  disabled={!hardwareAvailable}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium border rounded-lg hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset
                </button>
                <button
                  onClick={applyMotorPID}
                  disabled={!isConnected || !hardwareAvailable}
                  className={cn(
                    'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors',
                    'bg-blue-600 text-white hover:bg-blue-700',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  <Send className="w-3.5 h-3.5" />
                  Apply
                </button>
                <button
                  onClick={saveToFlash}
                  disabled={!isConnected || !hardwareAvailable}
                  className={cn(
                    'flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors',
                    'bg-green-600 text-white hover:bg-green-700',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                  title="Save to flash (persists across power cycles)"
                >
                  <Save className="w-3.5 h-3.5" />
                  Flash
                </button>
              </div>
            </div>
          )}

          {/* Yaw PID — Single Level */}
          {activeTab === 'yaw' && (
            <div className="space-y-3">
              <PIDSlider
                label="Kp (Proportional)"
                value={yawPID.kp}
                onChange={(v) => setYawPID((prev) => ({ ...prev, kp: v }))}
                disabled={!hardwareAvailable}
              />
              <PIDSlider
                label="Ki (Integral)"
                value={yawPID.ki}
                onChange={(v) => setYawPID((prev) => ({ ...prev, ki: v }))}
                max={2}
                disabled={!hardwareAvailable}
              />
              <PIDSlider
                label="Kd (Derivative)"
                value={yawPID.kd}
                onChange={(v) => setYawPID((prev) => ({ ...prev, kd: v }))}
                max={5}
                disabled={!hardwareAvailable}
              />

              {/* Yaw PID Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={resetYawPID}
                  disabled={!hardwareAvailable}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium border rounded-lg hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset
                </button>
                <button
                  onClick={applyYawPID}
                  disabled={!isConnected || !hardwareAvailable}
                  className={cn(
                    'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors',
                    'bg-blue-600 text-white hover:bg-blue-700',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  <Send className="w-3.5 h-3.5" />
                  Apply
                </button>
              </div>
            </div>
          )}

          {/* Connection/Hardware warnings */}
          {!isConnected && (
            <p className="text-xs text-yellow-500 text-center">
              Connect to ROS to apply PID changes
            </p>
          )}
          {isConnected && !hardwareAvailable && (
            <p className="text-xs text-red-500 text-center">
              Hardware node not running. Launch robot hardware first.
            </p>
          )}

          {/* Help text */}
          <p className="text-xs text-muted-foreground">
            {activeTab === 'motor'
              ? 'Single PID optimized for mid-speed autonomous navigation (100-300 mm/s). "Flash" persists settings across power cycles.'
              : 'Yaw PID controls rotation accuracy during straight-line motion.'}
          </p>
        </div>
      )}
    </div>
  );
}