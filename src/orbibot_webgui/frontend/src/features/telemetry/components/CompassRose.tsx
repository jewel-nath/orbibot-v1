/**
 * CompassRose - SVG compass displaying robot heading (yaw).
 * Heading 0° = North (ROS convention: 0 = +X axis forward).
 * The needle rotates with CSS transform for smooth 60fps animation.
 */

import { cn } from '@/lib/utils';

interface CompassRoseProps {
  /** Heading in degrees. 0 = facing +X (East on map = right). */
  heading: number;
  size?: number;
  className?: string;
}

export function CompassRose({ heading, size = 96, className }: CompassRoseProps) {
  const r = size / 2;
  const cx = r;
  const cy = r;

  // In ROS: yaw 0 = robot faces +X (East). On compass, 0° = North.
  // Convert: compass heading = 90 - yaw_deg so that 0° yaw points to East visually.
  // We rotate the needle by -heading so that the robot's forward direction points up.
  const needleRotation = -heading;

  // Tick marks at 0, 90, 180, 270
  const cardinals = [
    { angle: 0,   label: 'N', primary: true },
    { angle: 90,  label: 'E', primary: false },
    { angle: 180, label: 'S', primary: false },
    { angle: 270, label: 'W', primary: false },
  ];

  const toXY = (angleDeg: number, radius: number) => {
    const rad = (angleDeg - 90) * (Math.PI / 180);
    return { x: cx + Math.cos(rad) * radius, y: cy + Math.sin(rad) * radius };
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={cn('shrink-0', className)}
    >
      {/* Outer circle */}
      <circle
        cx={cx} cy={cy} r={r - 2}
        fill="none"
        stroke="hsl(var(--border))"
        strokeWidth={1}
      />
      {/* Background */}
      <circle
        cx={cx} cy={cy} r={r - 3}
        fill="hsl(var(--muted)/0.3)"
      />

      {/* Cardinal tick marks */}
      {cardinals.map(({ angle }) => {
        const outer = toXY(angle, r - 3);
        const inner = toXY(angle, r - 9);
        return (
          <line
            key={angle}
            x1={outer.x} y1={outer.y}
            x2={inner.x} y2={inner.y}
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={1.5}
            strokeLinecap="round"
          />
        );
      })}

      {/* Minor ticks at 45° increments */}
      {[45, 135, 225, 315].map(angle => {
        const outer = toXY(angle, r - 4);
        const inner = toXY(angle, r - 8);
        return (
          <line
            key={angle}
            x1={outer.x} y1={outer.y}
            x2={inner.x} y2={inner.y}
            stroke="hsl(var(--border))"
            strokeWidth={1}
            strokeLinecap="round"
          />
        );
      })}

      {/* Cardinal labels */}
      {cardinals.map(({ angle, label, primary }) => {
        const pos = toXY(angle, r - 16);
        return (
          <text
            key={label}
            x={pos.x}
            y={pos.y}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={size < 80 ? 7 : 9}
            fontWeight={primary ? '700' : '500'}
            fill={primary ? 'hsl(var(--primary))' : 'hsl(var(--muted-foreground))'}
          >
            {label}
          </text>
        );
      })}

      {/* Rotating needle group */}
      <g
        transform={`rotate(${needleRotation} ${cx} ${cy})`}
        style={{ transition: 'transform 0.3s ease-out' }}
      >
        {/* North half — primary color */}
        <polygon
          points={`${cx},${cy - r + 18} ${cx - 5},${cy + 4} ${cx + 5},${cy + 4}`}
          fill="hsl(var(--primary))"
          opacity={0.9}
        />
        {/* South half — muted */}
        <polygon
          points={`${cx},${cy + r - 18} ${cx - 5},${cy - 4} ${cx + 5},${cy - 4}`}
          fill="hsl(var(--muted-foreground))"
          opacity={0.5}
        />
        {/* Center dot */}
        <circle cx={cx} cy={cy} r={3} fill="hsl(var(--background))" stroke="hsl(var(--border))" strokeWidth={1} />
      </g>
    </svg>
  );
}
