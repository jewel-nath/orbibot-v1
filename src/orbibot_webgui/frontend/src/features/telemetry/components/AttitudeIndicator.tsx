/**
 * AttitudeIndicator - SVG artificial horizon showing roll and pitch.
 * Blue half = sky, brown half = ground. Horizon shifts up/down with pitch.
 * The sky/ground group rotates with roll. Center reference mark stays fixed.
 * Uses CSS transitions for smooth animation at 50Hz IMU rate.
 */

import { cn } from '@/lib/utils';

interface AttitudeIndicatorProps {
  roll: number;   // degrees; positive = right side down
  pitch: number;  // degrees; positive = nose up
  size?: number;
  className?: string;
}

const MAX_PITCH_PX_PER_DEG = 0.8; // pixels of horizon shift per degree of pitch

export function AttitudeIndicator({ roll, pitch, size = 80, className }: AttitudeIndicatorProps) {
  const r = size / 2;
  const cx = r;
  const cy = r;

  // Clamp pitch shift to keep horizon inside the circle
  const pitchShift = Math.max(-r * 0.8, Math.min(r * 0.8, pitch * MAX_PITCH_PX_PER_DEG));

  // Roll rotation: positive roll → right side goes down → rotate CW
  const rollDeg = roll;

  const clipId = `att-clip-${size}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={cn('shrink-0', className)}
    >
      <defs>
        <clipPath id={clipId}>
          <circle cx={cx} cy={cy} r={r - 2} />
        </clipPath>
      </defs>

      {/* Background (will be clipped to circle) */}
      <g clipPath={`url(#${clipId})`}>
        {/* Rotating group for roll */}
        <g
          transform={`rotate(${rollDeg} ${cx} ${cy})`}
          style={{ transition: 'transform 0.2s ease-out' }}
        >
          {/* Ground (bottom) */}
          <rect
            x={cx - size}
            y={cy + pitchShift}
            width={size * 2}
            height={size * 2}
            fill="hsl(30 40% 35%)"
            opacity={0.9}
          />
          {/* Sky (top) */}
          <rect
            x={cx - size}
            y={cy - size * 2 + pitchShift}
            width={size * 2}
            height={size * 2}
            fill="hsl(var(--primary)/0.35)"
          />
          {/* Horizon line */}
          <line
            x1={cx - size}
            y1={cy + pitchShift}
            x2={cx + size}
            y2={cy + pitchShift}
            stroke="white"
            strokeWidth={1.5}
            opacity={0.8}
          />
          {/* Pitch scale lines (±10°) */}
          {[-20, -10, 10, 20].map(deg => {
            const shift = pitchShift - deg * MAX_PITCH_PX_PER_DEG;
            const lineW = deg % 20 === 0 ? 24 : 14;
            return (
              <line
                key={deg}
                x1={cx - lineW / 2}
                y1={cy + shift}
                x2={cx + lineW / 2}
                y2={cy + shift}
                stroke="white"
                strokeWidth={1}
                opacity={0.5}
              />
            );
          })}
        </g>
      </g>

      {/* Outer ring */}
      <circle
        cx={cx} cy={cy} r={r - 2}
        fill="none"
        stroke="hsl(var(--border))"
        strokeWidth={1.5}
      />

      {/* Fixed reference mark (aircraft wings — not affected by roll) */}
      <g stroke="white" strokeWidth={2} strokeLinecap="round" opacity={0.9}>
        {/* Left wing */}
        <line x1={cx - r + 6} y1={cy} x2={cx - r / 2 + 4} y2={cy} />
        <line x1={cx - r / 2 + 4} y1={cy} x2={cx - r / 2 + 4} y2={cy + 4} />
        {/* Right wing */}
        <line x1={cx + r - 6} y1={cy} x2={cx + r / 2 - 4} y2={cy} />
        <line x1={cx + r / 2 - 4} y1={cy} x2={cx + r / 2 - 4} y2={cy + 4} />
        {/* Center dot */}
        <circle cx={cx} cy={cy} r={2} fill="white" stroke="none" />
      </g>
    </svg>
  );
}
