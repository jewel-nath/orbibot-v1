/**
 * WheelCalibrationWizard - Multi-step wizard for wheel calibration and CPR verification.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { useEncoders } from '@/hooks/useEncoders';
import { useOdometry } from '@/hooks/useOdometry';
import { useCmdVel } from '@/hooks/useCmdVel';
import { Button } from '@/components/ui/button';
import { MOTOR_MAPPING } from '@/lib/constants';
import { CheckCircle2, XCircle, Play, RotateCcw, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const TEST_VELOCITY = 0.15; // m/s
const TEST_DURATION_MS = 5000;
const CMD_INTERVAL_MS = 50;
const EXPECTED_CPR = 1320;
const WHEEL_RADIUS = 0.05;

type Step = 'prepare' | 'running' | 'results';

interface CalibrationResult {
  motor: string;
  abbreviation: string;
  encoderDelta: number;
  expectedDelta: number;
  ratio: number;
  pass: boolean;
}

export function WheelCalibrationWizard() {
  const { ros, connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';
  const encoders = useEncoders();
  const odom = useOdometry();
  const { publishVelocity, stop } = useCmdVel();

  const [step, setStep] = useState<Step>('prepare');
  const [results, setResults] = useState<CalibrationResult[]>([]);
  const [progress, setProgress] = useState(0);

  const startEncodersRef = useRef<number[]>([0, 0, 0, 0]);
  const startOdomRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const resetServices = useCallback(() => {
    if (!ros || !isConnected) return;

    // Reset encoders
    const encoderSrv = new ROSLIB.Service({
      ros,
      name: '/orbibot/reset_encoders',
      serviceType: 'orbibot_msgs/srv/ResetEncoders',
    });
    encoderSrv.callService(new ROSLIB.ServiceRequest({}), () => {}, () => {});

    // Reset odometry
    const odomSrv = new ROSLIB.Service({
      ros,
      name: '/orbibot/reset_odometry',
      serviceType: 'orbibot_msgs/srv/ResetOdometry',
    });
    odomSrv.callService(new ROSLIB.ServiceRequest({}), () => {}, () => {});
  }, [ros, isConnected]);

  const startTest = useCallback(() => {
    if (!encoders?.data || !odom) return;

    // Record starting values
    startEncodersRef.current = [...(encoders.data ?? [0, 0, 0, 0])];
    startOdomRef.current = { x: odom.x, y: odom.y };

    setStep('running');
    setProgress(0);

    // Progress timer
    const startTime = Date.now();
    progressRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime;
      setProgress(Math.min(elapsed / TEST_DURATION_MS, 1));
    }, 100);

    // Command velocity
    intervalRef.current = setInterval(() => {
      publishVelocity({ vx: TEST_VELOCITY, vy: 0, wz: 0 });
    }, CMD_INTERVAL_MS);

    // Stop after duration
    timeoutRef.current = setTimeout(() => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (progressRef.current) clearInterval(progressRef.current);
      intervalRef.current = null;
      progressRef.current = null;
      stop();
      setProgress(1);

      // Wait a moment for final encoder update
      setTimeout(() => {
        computeResults();
      }, 500);
    }, TEST_DURATION_MS);
  }, [encoders, odom, publishVelocity, stop]);

  const computeResults = useCallback(() => {
    if (!encoders?.data || !odom) {
      setStep('prepare');
      return;
    }

    const endEncoders = encoders.data;
    const distance = Math.sqrt(
      (odom.x - startOdomRef.current.x) ** 2 +
      (odom.y - startOdomRef.current.y) ** 2
    );

    // Expected encoder delta for the traveled distance
    const expectedDelta = (distance / (2 * Math.PI * WHEEL_RADIUS)) * EXPECTED_CPR;

    const motorResults: CalibrationResult[] = MOTOR_MAPPING.map((motor, i) => {
      const delta = Math.abs(endEncoders[i] - startEncodersRef.current[i]);
      const ratio = expectedDelta > 0 ? delta / expectedDelta : 0;
      return {
        motor: motor.name,
        abbreviation: motor.abbreviation,
        encoderDelta: delta,
        expectedDelta: Math.round(expectedDelta),
        ratio,
        pass: ratio > 0.7 && ratio < 1.3,
      };
    });

    setResults(motorResults);
    setStep('results');
  }, [encoders, odom]);

  const reset = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (progressRef.current) clearInterval(progressRef.current);
    stop();
    setStep('prepare');
    setResults([]);
    setProgress(0);
  }, [stop]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (progressRef.current) clearInterval(progressRef.current);
    };
  }, []);

  return (
    <div className="space-y-4">
      {/* Step indicator */}
      <div className="flex items-center gap-2 text-xs">
        {(['prepare', 'running', 'results'] as const).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            {i > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground" />}
            <span
              className={cn(
                'px-2 py-0.5 rounded-full font-medium',
                step === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
              )}
            >
              {i + 1}. {s === 'prepare' ? 'Prepare' : s === 'running' ? 'Drive Test' : 'Results'}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Prepare */}
      {step === 'prepare' && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Place the robot on a flat surface with clear space ahead (~1m). This test drives the robot forward
            at {TEST_VELOCITY} m/s for {TEST_DURATION_MS / 1000}s and compares encoder counts against expected values.
          </p>
          <div className="flex gap-2">
            <Button onClick={resetServices} variant="outline" size="sm" className="gap-1.5" disabled={!isConnected}>
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Encoders & Odometry
            </Button>
            <Button onClick={startTest} size="sm" className="gap-1.5" disabled={!isConnected}>
              <Play className="w-3.5 h-3.5" />
              Start Drive Test
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Running */}
      {step === 'running' && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Driving forward at {TEST_VELOCITY} m/s...
          </p>
          <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-200"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <div className="text-xs font-mono text-muted-foreground text-center">
            {(progress * TEST_DURATION_MS / 1000).toFixed(1)}s / {TEST_DURATION_MS / 1000}s
          </div>
          <Button onClick={reset} variant="outline" size="sm">Cancel</Button>
        </div>
      )}

      {/* Step 3: Results */}
      {step === 'results' && (
        <div className="space-y-3">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="text-left py-2 font-medium">Motor</th>
                <th className="text-right py-2 font-medium">Encoder Delta</th>
                <th className="text-right py-2 font-medium">Expected</th>
                <th className="text-right py-2 font-medium">Ratio</th>
                <th className="text-center py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {results.map(r => (
                <tr key={r.motor} className="border-b border-border/40">
                  <td className="py-1.5 font-medium">{r.motor} ({r.abbreviation})</td>
                  <td className="py-1.5 text-right font-mono">{r.encoderDelta.toLocaleString()}</td>
                  <td className="py-1.5 text-right font-mono">{r.expectedDelta.toLocaleString()}</td>
                  <td className="py-1.5 text-right font-mono">{r.ratio.toFixed(2)}x</td>
                  <td className="py-1.5 text-center">
                    {r.pass ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500 inline" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500 inline" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-muted-foreground">
            A ratio near 1.0 indicates correct CPR configuration ({EXPECTED_CPR} PPR).
            Values below 0.7 or above 1.3 suggest encoder misconfiguration.
          </p>
          <Button onClick={reset} variant="outline" size="sm" className="gap-1.5">
            <RotateCcw className="w-3.5 h-3.5" />
            Run Again
          </Button>
        </div>
      )}
    </div>
  );
}
