/**
 * PIDTuningPanel - Multi-level PID gain tuning interface
 *
 * Features:
 * - 3-level motor PID gains (low/medium/high speed) with speed thresholds
 * - Yaw PID gains tab
 * - Per-level slider controls with numeric input
 * - Apply sends gains to firmware, Save persists to flash
 * - Reset to defaults
 *
 * Topics Published:
 * - /orbibot/pid_params (Float32MultiArray) - [kp, ki, kd] (single-level compat)
 * - /orbibot/yaw_pid_params (Float32MultiArray) - [kp, ki, kd]
 * - /orbibot/pid_multilevel (Float32MultiArray) - [t0,t1,t2,kp0,ki0,kd0,kp1,ki1,kd1,kp2,ki2,kd2]
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

// Default multi-level PID values matching firmware orbibot_config.h
const DEFAULT_PID_LEVELS = [
  { kp: 1.2, ki: 0.04, kd: 0.6, label: 'Low Speed' },
  { kp: 0.8, ki: 0.06, kd: 0.5, label: 'Medium Speed' },
  { kp: 0.5, ki: 0.08, kd: 0.4, label: 'High Speed' },
];

const DEFAULT_SPEED_THRESHOLDS = [50, 200, 500]; // mm/s

const DEFAULT_YAW_PID = { kp: 1.0, ki: 0.0, kd: 0.1 };

// PID parameter limits (firmware accepts 0-10)
const PID_MIN = 0;
const PID_MAX = 10;
const PID_STEP = 0.01;
const SPEED_MIN = 0;
const SPEED_MAX = 1000;
const SPEED_STEP = 10;

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
            onChange(Math.max(min, Math.min(max, val)));  // Clamp to min/max range
          }}
          onBlur={(e) => {
            // Ensure value is clamped on blur as well
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

function LevelGainsEditor({
  level,
  label,
  gains,
  threshold,
  onGainsChange,
  onThresholdChange,
  disabled,
}: {
  level: number;
  label: string;
  gains: PIDGains;
  threshold: number;
  onGainsChange: (gains: PIDGains) => void;
  onThresholdChange: (threshold: number) => void;
  disabled: boolean;
}) {
  return (
    <div className="space-y-2 p-2 bg-muted/30 rounded-md">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground">
          L{level}: {label}
        </span>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-muted-foreground">Threshold:</span>
          <input
            type="number"
            value={threshold}
            onChange={(e) => {
              const val = parseFloat(e.target.value) || 0;
              onThresholdChange(Math.max(SPEED_MIN, Math.min(SPEED_MAX, val)));  // G16: Clamp to min/max range
            }}
            min={SPEED_MIN}
            max={SPEED_MAX}
            step={SPEED_STEP}
            disabled={disabled}
            className="w-14 px-1 py-0.5 text-[10px] text-right bg-muted border rounded disabled:opacity-50"
          />
          <span className="text-[10px] text-muted-foreground">mm/s</span>
        </div>
      </div>
      <PIDSlider
        label="Kp"
        value={gains.kp}
        onChange={(v) => onGainsChange({ ...gains, kp: v })}
        disabled={disabled}
      />
      <PIDSlider
        label="Ki"
        value={gains.ki}
        onChange={(v) => onGainsChange({ ...gains, ki: v })}
        max={2}
        disabled={disabled}
      />
      <PIDSlider
        label="Kd"
        value={gains.kd}
        onChange={(v) => onGainsChange({ ...gains, kd: v })}
        max={5}
        disabled={disabled}
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

  // Multi-level PID state
  const [pidLevels, setPidLevels] = useState<PIDGains[]>(
    DEFAULT_PID_LEVELS.map(({ kp, ki, kd }) => ({ kp, ki, kd }))
  );
  const [speedThresholds, setSpeedThresholds] = useState([...DEFAULT_SPEED_THRESHOLDS]);
  const [yawPID, setYawPID] = useState<PIDGains>({ ...DEFAULT_YAW_PID });

  // Publisher refs
  const multilevelPubRef = useRef<ROSLIB.Topic | null>(null);
  const savePubRef = useRef<ROSLIB.Topic | null>(null);
  const yawPubRef = useRef<ROSLIB.Topic | null>(null);

  // Setup publishers
  useEffect(() => {
    if (!ros || !isConnected) {
      multilevelPubRef.current = null;
      savePubRef.current = null;
      yawPubRef.current = null;
      return;
    }

    multilevelPubRef.current = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.pidMultilevel,
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
      multilevelPubRef.current = null;
      savePubRef.current = null;
      yawPubRef.current = null;
    };
  }, [ros, isConnected]);

  // Apply multi-level PID (sends to firmware RAM, not flash)
  const applyMotorPID = useCallback(() => {
    if (!multilevelPubRef.current) {
      toast.error('Not connected to ROS');
      return;
    }

    // Format: [t0, t1, t2, kp0, ki0, kd0, kp1, ki1, kd1, kp2, ki2, kd2]
    const data = [
      ...speedThresholds,
      ...pidLevels.flatMap((l) => [l.kp, l.ki, l.kd]),
    ];

    multilevelPubRef.current.publish(new ROSLIB.Message({ data }));

    toast.success('Multi-level PID applied', {
      description: pidLevels
        .map(
          (l, i) =>
            `L${i}: Kp=${l.kp.toFixed(2)} Ki=${l.ki.toFixed(2)} Kd=${l.kd.toFixed(2)}`
        )
        .join(' | '),
    });
  }, [pidLevels, speedThresholds]);

  // Save to flash
  const saveToFlash = useCallback(() => {
    if (!savePubRef.current) {
      toast.error('Not connected to ROS');
      return;
    }

    // First apply, then save (send all levels + thresholds for multilevel PID)
    applyMotorPID();

    // Format: [t0, t1, t2, kp0, ki0, kd0, kp1, ki1, kd1, kp2, ki2, kd2]
    const data = [
      ...speedThresholds,  // t0, t1, t2
      ...pidLevels.flatMap(level => [level.kp, level.ki, level.kd])  // all 3 levels
    ];
    savePubRef.current.publish(new ROSLIB.Message({ data }));

    toast.success('Multilevel PID gains saved to flash', {
      description: 'All 3 levels + thresholds will persist across power cycles',
    });
  }, [pidLevels, speedThresholds, applyMotorPID]);

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
    setPidLevels(DEFAULT_PID_LEVELS.map(({ kp, ki, kd }) => ({ kp, ki, kd })));
    setSpeedThresholds([...DEFAULT_SPEED_THRESHOLDS]);
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

          {/* Motor PID — 3-Level Editor */}
          {activeTab === 'motor' && (
            <div className="space-y-2">
              {pidLevels.map((gains, i) => (
                <LevelGainsEditor
                  key={i}
                  level={i}
                  label={DEFAULT_PID_LEVELS[i].label}
                  gains={gains}
                  threshold={speedThresholds[i]}
                  onGainsChange={(g) =>
                    setPidLevels((prev) => prev.map((p, j) => (j === i ? g : p)))
                  }
                  onThresholdChange={(t) =>
                    setSpeedThresholds((prev) =>
                      prev.map((p, j) => (j === i ? t : p))
                    )
                  }
                  disabled={!hardwareAvailable}
                />
              ))}

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
              ? '3-level PID: gains interpolate between speed thresholds. Low speed uses high Kp for crisp starts, high speed uses lower Kp to reduce oscillation. "Flash" persists settings across power cycles.'
              : 'Yaw PID controls rotation accuracy during straight-line motion.'}
          </p>
        </div>
      )}
    </div>
  );
}
