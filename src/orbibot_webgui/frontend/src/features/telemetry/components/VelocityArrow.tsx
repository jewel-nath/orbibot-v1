/**
 * VelocityArrow - SVG circular indicator showing velocity vector direction and magnitude.
 * Arrow direction = atan2(vy, vx). Arrow length scales with speed (clamped to radius).
 * A separate curved arc shows rotation direction (wz).
 * Stationary → faint dot. Moving → solid directional arrow.
 */

import { cn } from '@/lib/utils';

interface VelocityArrowProps {
  vx: number;    // m/s forward
  vy: number;    // m/s lateral (positive = left in ROS)
  wz: number;    // rad/s angular
  size?: number;
  className?: string;
}

const MAX_SPEED = 1.0; // m/s — full arrow length at this speed

export function VelocityArrow({ vx, vy, wz, size = 80, className }: VelocityArrowProps) {
  const r = size / 2;
  const cx = r;
  const cy = r;
  const innerR = r - 6;

  const speed = Math.sqrt(vx * vx + vy * vy);
  const isMoving = speed > 0.01;
  const isRotating = Math.abs(wz) > 0.05;

  // Direction angle: atan2(vy, vx) in degrees.
  // In ROS: +x = forward, +y = left.
  // On screen SVG: +x = right, +y = down.
  // We want: forward (vx>0) → arrow points up; left (vy>0) → arrow points left.
  // So screen angle = -(atan2(vy, vx) + 90°) ... let's derive:
  // Robot forward = up on screen, so rotate 90° CCW from standard math angle.
  const dirRad = Math.atan2(vy, vx);        // standard math angle (CCW from +x)
  const screenDeg = -(dirRad * 180 / Math.PI) + 90; // convert: fwd=up

  // Arrow length proportional to speed, max = innerR * 0.75
  const arrowLen = Math.min(speed / MAX_SPEED, 1) * innerR * 0.75;

  const tipX = cx + Math.sin(dirRad) * arrowLen * -1;  // screen coords
  const tipY = cy - Math.cos(dirRad) * arrowLen;       // up = fwd
  // Use the computed screenDeg for the arrowhead rotation
  void screenDeg; // used implicitly through tipX/tipY

  // Rotation indicator arc
  const rotRadius = innerR - 6;
  const rotAngle = Math.min(Math.abs(wz) / 2.0, 0.7) * Math.PI; // max ~126°
  const rotDir = wz > 0 ? 1 : -1; // positive wz = CCW in ROS

  // Arc from top-right to right (CW for +wz = turning right... wait, ROS +wz = CCW = turn left)
  // We draw a small arc in the rotation direction
  const arcStartAngle = -Math.PI / 2 - 0.2; // near top
  const arcEndAngle = arcStartAngle + rotDir * rotAngle;
  const arcX1 = cx + Math.cos(arcStartAngle) * rotRadius;
  const arcY1 = cy + Math.sin(arcStartAngle) * rotRadius;
  const arcX2 = cx + Math.cos(arcEndAngle) * rotRadius;
  const arcY2 = cy + Math.sin(arcEndAngle) * rotRadius;
  const largeArc = rotAngle > Math.PI ? 1 : 0;
  const sweepFlag = rotDir > 0 ? 1 : 0;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={cn('shrink-0', className)}
    >
      {/* Outer ring */}
      <circle
        cx={cx} cy={cy} r={r - 2}
        fill="none"
        stroke="hsl(var(--border))"
        strokeWidth={1}
      />
      {/* Background */}
      <circle
        cx={cx} cy={cy} r={r - 3}
        fill="hsl(var(--muted)/0.2)"
      />

      {/* Cross-hairs (faint) */}
      <line x1={cx} y1={cy - innerR + 4} x2={cx} y2={cy + innerR - 4}
        stroke="hsl(var(--border))" strokeWidth={0.5} opacity={0.5} />
      <line x1={cx - innerR + 4} y1={cy} x2={cx + innerR - 4} y2={cy}
        stroke="hsl(var(--border))" strokeWidth={0.5} opacity={0.5} />

      {/* Rotation arc */}
      {isRotating && (
        <path
          d={`M ${arcX1} ${arcY1} A ${rotRadius} ${rotRadius} 0 ${largeArc} ${sweepFlag} ${arcX2} ${arcY2}`}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          strokeLinecap="round"
          opacity={0.6}
        />
      )}

      {/* Velocity arrow or stationary dot */}
      {isMoving ? (
        <g style={{ transition: 'all 0.2s ease-out' }}>
          {/* Arrow shaft */}
          <line
            x1={cx} y1={cy}
            x2={tipX} y2={tipY}
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            strokeLinecap="round"
          />
          {/* Arrowhead */}
          <circle cx={tipX} cy={tipY} r={3} fill="hsl(var(--primary))" />
        </g>
      ) : (
        <circle
          cx={cx} cy={cy} r={3}
          fill="hsl(var(--muted-foreground))"
          opacity={0.4}
        />
      )}
    </svg>
  );
}
