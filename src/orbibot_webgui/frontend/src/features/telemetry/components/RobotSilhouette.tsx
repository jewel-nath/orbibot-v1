/**
 * RobotSilhouette - Top-down SVG robot body with 4 mecanum wheels.
 * Wheel color: green = enabled, red = fault/disabled.
 * Encoder counts shown below each wheel position.
 * Aspect ratio based on OrbiBot footprint: 350mm × 250mm → 7:5.
 */

import { cn } from '@/lib/utils';

interface WheelData {
  id: number;
  label: string;        // "FL", "BL", "FR", "BR"
  encoderCount: number;
  enabled: boolean;
  hasFault?: boolean;
}

interface RobotSilhouetteProps {
  wheels: WheelData[];
  width?: number;
  className?: string;
}

export function RobotSilhouette({ wheels, width = 160, className }: RobotSilhouetteProps) {
  // Maintain 7:5 aspect (350mm wide, 250mm long)
  const W = width;
  const H = Math.round(W * (250 / 350));
  const cx = W / 2;
  const cy = H / 2;

  // Body rectangle — 65% of total width/height (wheels protrude outside)
  const bodyW = W * 0.54;
  const bodyH = H * 0.54;

  // Wheel dimensions
  const wheelW = W * 0.14;
  const wheelH = H * 0.3;
  const wheelR = 3;

  // Wheel center positions (matching FL/BL/FR/BR corners)
  const wheelPositions = [
    { label: 'FL', x: cx - bodyW / 2 - wheelW * 0.15, y: cy - bodyH / 2 + wheelH * 0.25 },
    { label: 'BL', x: cx - bodyW / 2 - wheelW * 0.15, y: cy + bodyH / 2 - wheelH * 0.25 },
    { label: 'FR', x: cx + bodyW / 2 + wheelW * 0.15, y: cy - bodyH / 2 + wheelH * 0.25 },
    { label: 'BR', x: cx + bodyW / 2 + wheelW * 0.15, y: cy + bodyH / 2 - wheelH * 0.25 },
  ];

  const wheelColor = (w: WheelData) => {
    if (w.hasFault) return '#ef4444';       // red-500
    if (!w.enabled) return 'hsl(var(--muted-foreground))';
    return '#22c55e';                        // green-500
  };

  const wheelStroke = (w: WheelData) => {
    if (w.hasFault) return '#dc2626';
    if (!w.enabled) return 'hsl(var(--border))';
    return '#16a34a';
  };

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      className={cn('shrink-0', className)}
    >
      {/* Body shadow / glow */}
      <rect
        x={cx - bodyW / 2 + 2}
        y={cy - bodyH / 2 + 2}
        width={bodyW}
        height={bodyH}
        rx={6}
        fill="hsl(var(--primary)/0.08)"
      />

      {/* Robot body */}
      <rect
        x={cx - bodyW / 2}
        y={cy - bodyH / 2}
        width={bodyW}
        height={bodyH}
        rx={5}
        fill="hsl(var(--card))"
        stroke="hsl(var(--border))"
        strokeWidth={1.5}
      />

      {/* Forward arrow on body */}
      <polygon
        points={`${cx},${cy - bodyH / 2 + 8} ${cx - 7},${cy - bodyH / 2 + 20} ${cx + 7},${cy - bodyH / 2 + 20}`}
        fill="hsl(var(--primary))"
        opacity={0.7}
      />

      {/* Wheels */}
      {wheelPositions.map(pos => {
        const w = wheels.find(wh => wh.label === pos.label);
        if (!w) return null;
        return (
          <g key={pos.label}>
            <rect
              x={pos.x - wheelW / 2}
              y={pos.y - wheelH / 2}
              width={wheelW}
              height={wheelH}
              rx={wheelR}
              fill={wheelColor(w)}
              stroke={wheelStroke(w)}
              strokeWidth={1}
              opacity={0.85}
            />
          </g>
        );
      })}
    </svg>
  );
}
