/**
 * MapView - SLAM occupancy grid visualization with robot pose overlay
 *
 * Features:
 * - Occupancy grid rendering (-1=unknown, 0=free, 100=occupied)
 * - Robot pose from odometry (green arrow)
 * - Zoom, pan, reset controls
 * - Click-to-pose for init_pose, nav_goal, waypoint modes
 * - Path display from /plan topic
 * - Waypoint markers
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useMap } from '@/hooks/useMap';
import { useOdometry } from '@/hooks/useOdometry';
import { useRobotMapPose } from '@/hooks/useRobotMapPose';
import { useNavigationContext } from '@/contexts/NavigationContext';
import { useInitialPose } from '@/hooks/useInitialPose';
import { useNavGoal } from '@/hooks/useNavGoal';
import { cn } from '@/lib/utils';
import { Map, ZoomIn, ZoomOut, Maximize2, RotateCw, Lock } from 'lucide-react';
import type { InteractionMode } from '@/types/interaction';

// Colors for different interaction modes
const MODE_COLORS: Record<InteractionMode, string> = {
  none: 'transparent',
  init_pose: '#22c55e',    // Green
  nav_goal: '#3b82f6',     // Blue
  waypoint: '#f97316',     // Orange
};

interface MapViewProps {
  className?: string;
}

export function MapView({ className }: MapViewProps) {
  const map = useMap();
  const odom = useOdometry();
  const robotMapPose = useRobotMapPose(); // map-frame pose (amcl or odom fallback)
  const { mode, setMode, path, waypoints, addWaypoint } = useNavigationContext();
  const { publishInitialPose } = useInitialPose();
  const { sendGoal } = useNavGoal();

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [scale, setScale] = useState(1.0);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Map rotation state
  const [rotation, setRotation] = useState(0); // Degrees
  const [trackUp, setTrackUp] = useState(false);

  // Pose setting state
  const [isDraggingPose, setIsDraggingPose] = useState(false);
  const [poseStart, setPoseStart] = useState<{ x: number; y: number } | null>(null);
  const [poseEnd, setPoseEnd] = useState<{ x: number; y: number } | null>(null);

  // Reset view
  const handleReset = () => {
    setScale(1.0);
    setOffset({ x: 0, y: 0 });
    setRotation(0);
    setTrackUp(false);
  };

  // Zoom controls
  const handleZoomIn = () => setScale((s) => Math.min(s * 1.2, 5.0));
  const handleZoomOut = () => setScale((s) => Math.max(s / 1.2, 0.2));

  // Compute pixels-per-meter so the map auto-fits the container
  // Auto-rotate map if Track Up is enabled
  useEffect(() => {
    if (trackUp && robotMapPose) {
      setRotation(-(robotMapPose.theta * 180 / Math.PI) - 90);
    }
  }, [trackUp, robotMapPose]);

  // Compute pixels-per-meter so the map auto-fits the container
  const computeFitScale = useCallback(() => {
    if (!map || !containerRef.current) return 1;
    const { width, height, resolution } = map.info;
    const cw = containerRef.current.clientWidth;
    const ch = containerRef.current.clientHeight;
    const mapWorldW = width * resolution;
    const mapWorldH = height * resolution;
    // Fit to 85% of container
    return Math.min((cw * 0.85) / mapWorldW, (ch * 0.85) / mapWorldH);
  }, [map]);

  // Convert canvas pixel to map coordinates
  const canvasToMap = useCallback(
    (canvasX: number, canvasY: number): { x: number; y: number } | null => {
      if (!map || !containerRef.current) return null;

      const { info } = map;
      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const fitScale = computeFitScale();
      const effectiveScale = fitScale * scale;

      // Get position relative to canvas center
      const centerX = container.clientWidth / 2 + offset.x;
      const centerY = container.clientHeight / 2 + offset.y;

      // Screen-space offsets from center
      const screenX = (canvasX - rect.left - centerX) / effectiveScale;
      const screenY = (canvasY - rect.top - centerY) / effectiveScale;

      // Apply inverse rotation matrix: R(-θ) not R(θ) - G13 fix
      const r = (rotation * Math.PI) / 180;
      const cos = Math.cos(r);
      const sin = Math.sin(r);

      const dx = screenX * cos + screenY * sin;
      const dy = screenX * sin - screenY * cos;

      // Convert from meters offset to map coordinates (global frame)
      const mapX = dx + info.origin.position.x + (info.width * info.resolution) / 2;
      const mapY = dy + info.origin.position.y + (info.height * info.resolution) / 2;

      return { x: mapX, y: mapY };
    },
    [map, scale, offset, computeFitScale, rotation]
  );

  // Handle mouse down for pose setting or panning
  const handleMouseDown = (e: React.MouseEvent) => {
    if (mode !== 'none' && map) {
      // Start pose drag
      const mapPos = canvasToMap(e.clientX, e.clientY);
      if (mapPos) {
        setIsDraggingPose(true);
        setPoseStart(mapPos);
        setPoseEnd(mapPos);
      }
    } else {
      // Start panning
      setIsPanning(true);
      setPanStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    }
  };

  // Handle mouse move
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDraggingPose && poseStart) {
      // Update pose end for orientation
      const mapPos = canvasToMap(e.clientX, e.clientY);
      if (mapPos) {
        setPoseEnd(mapPos);
      }
    } else if (isPanning) {
      // Update pan offset
      setOffset({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    }
  };

  // Handle mouse up - finalize pose
  const handleMouseUp = () => {
    if (isDraggingPose && poseStart && poseEnd) {
      // Calculate orientation from drag direction
      const dx = poseEnd.x - poseStart.x;
      const dy = poseEnd.y - poseStart.y;
      const theta = Math.atan2(dy, dx);

      // Execute action based on mode
      switch (mode) {
        case 'init_pose':
          publishInitialPose(poseStart.x, poseStart.y, theta);
          break;
        case 'nav_goal':
          sendGoal(poseStart.x, poseStart.y, theta);
          break;
        case 'waypoint':
          addWaypoint({
            name: `Waypoint ${waypoints.length + 1}`,
            x: poseStart.x,
            y: poseStart.y,
            theta,
          });
          break;
      }

      // Reset mode after action
      setMode('none');
    }

    // Reset states
    setIsDraggingPose(false);
    setPoseStart(null);
    setPoseEnd(null);
    setIsPanning(false);
  };

  // Render map on canvas
  useEffect(() => {
    if (!canvasRef.current || !containerRef.current || !map) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const container = containerRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const dpr = window.devicePixelRatio || 1;

    // Set canvas size to physical pixels for sharp rendering
    canvas.width = Math.round(containerWidth * dpr);
    canvas.height = Math.round(containerHeight * dpr);
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${containerHeight}px`;

    // Scale context so drawing uses CSS pixels, rendered at physical resolution
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;

    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, containerWidth, containerHeight);

    const { info, data } = map;
    const { width, height, resolution, origin } = info;

    const centerX = containerWidth / 2 + offset.x;
    const centerY = containerHeight / 2 + offset.y;

    // Auto-fit: compute pixels-per-meter so map fills container
    const fitScale = computeFitScale();
    const effectiveScale = fitScale * scale;

    // Create image data for the map
    const imageData = ctx.createImageData(width, height);

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const index = y * width + x;
        const occupancy = data[index];
        const pixelIndex = (y * width + x) * 4;

        if (occupancy === -1) {
          imageData.data[pixelIndex] = 128;
          imageData.data[pixelIndex + 1] = 128;
          imageData.data[pixelIndex + 2] = 128;
          imageData.data[pixelIndex + 3] = 255;
        } else if (occupancy === 0) {
          imageData.data[pixelIndex] = 255;
          imageData.data[pixelIndex + 1] = 255;
          imageData.data[pixelIndex + 2] = 255;
          imageData.data[pixelIndex + 3] = 255;
        } else {
          const intensity = Math.max(0, 255 - occupancy * 2.55);
          imageData.data[pixelIndex] = intensity;
          imageData.data[pixelIndex + 1] = intensity;
          imageData.data[pixelIndex + 2] = intensity;
          imageData.data[pixelIndex + 3] = 255;
        }
      }
    }

    // Create temporary canvas for the map
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext('2d');
    if (tempCtx) {
      tempCtx.putImageData(imageData, 0, 0);

      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate((rotation * Math.PI) / 180); // Apply map rotation
      ctx.scale(effectiveScale, -effectiveScale);
      ctx.translate(-width * resolution / 2, -height * resolution / 2);
      ctx.drawImage(tempCanvas, 0, 0, width * resolution, height * resolution);
      ctx.restore();
    }

    // Helper function to convert map coords to canvas coords
    const mapToCanvas = (mx: number, my: number) => {
      // 1. Center relative to map center (meters)
      let dx = (mx - origin.position.x) - (width * resolution) / 2;
      let dy = (my - origin.position.y) - (height * resolution) / 2;

      // 2. Apply rotation matrix [cos sin; sin -cos] (matches Canvas R * S)
      const r = (rotation * Math.PI) / 180;
      const cos = Math.cos(r);
      const sin = Math.sin(r);

      const dx_screen = dx * cos + dy * sin;
      const dy_screen = dx * sin - dy * cos;

      // 3. Scale and Translate to Screen Center
      const px = dx_screen * effectiveScale + centerX;
      const py = dy_screen * effectiveScale + centerY;

      return { x: px, y: py };
    };

    // Draw path if available
    if (path.length > 1) {
      ctx.save();
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();

      const firstPoint = mapToCanvas(path[0].x, path[0].y);
      ctx.moveTo(firstPoint.x, firstPoint.y);

      for (let i = 1; i < path.length; i++) {
        const point = mapToCanvas(path[i].x, path[i].y);
        ctx.lineTo(point.x, point.y);
      }

      ctx.stroke();
      ctx.restore();
    }

    // Draw waypoints
    waypoints.forEach((wp, index) => {
      const pos = mapToCanvas(wp.x, wp.y);
      const arrowSize = 15;

      ctx.save();
      ctx.translate(pos.x, pos.y);
      ctx.rotate(-wp.theta);

      // Waypoint arrow
      ctx.fillStyle = '#f97316';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;

      ctx.beginPath();
      ctx.moveTo(arrowSize, 0);
      ctx.lineTo(-arrowSize / 2, arrowSize / 2);
      ctx.lineTo(-arrowSize / 2, -arrowSize / 2);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.restore();

      // Waypoint number
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${index + 1}`, pos.x, pos.y);
    });

    // Draw robot pose (Car Icon) — uses map-frame pose (amcl_pose when available,
    // falls back to /odometry/filtered). This correctly reflects Init Pose updates.
    const displayPose = robotMapPose;
    if (displayPose) {
      const robotPos = mapToCanvas(displayPose.x, displayPose.y);
      // theta from useRobotMapPose is in radians; convert to degrees for visualTheta
      const thetaDeg = displayPose.theta * (180 / Math.PI);
      const visualTheta = (thetaDeg - rotation) * (Math.PI / 180);

      // Real robot dimensions (meters) → screen pixels
      const realLength = 0.35 * effectiveScale;
      const realWidth = 0.25 * effectiveScale;
      // Minimum 20px length for visibility when zoomed out
      const minScale = Math.max(1, 20 / realLength);
      const carLength = realLength * minScale;
      const carWidth = realWidth * minScale;

      ctx.save();
      ctx.translate(robotPos.x, robotPos.y);
      ctx.rotate(-visualTheta);

      // Car Body
      ctx.fillStyle = '#22c55e';
      ctx.shadowColor = 'rgba(0,0,0,0.5)';
      ctx.shadowBlur = 10;

      ctx.beginPath();
      ctx.roundRect(-carLength / 2, -carWidth / 2, carLength, carWidth, carLength / 6);
      ctx.fill();

      // Windshield / Front indicator
      ctx.fillStyle = '#103015';
      ctx.beginPath();
      ctx.roundRect(carLength / 4, -carWidth / 2 + carWidth * 0.1, carLength / 4, carWidth * 0.8, carLength / 24);
      ctx.fill();

      // Headlights
      ctx.fillStyle = '#fbbf24';
      ctx.shadowColor = '#fbbf24';
      ctx.shadowBlur = 5;
      ctx.beginPath();
      ctx.arc(carLength / 2, -carWidth / 3, carLength / 12, 0, Math.PI * 2);
      ctx.arc(carLength / 2, carWidth / 3, carLength / 12, 0, Math.PI * 2);
      ctx.fill();

      // Wheels
      ctx.fillStyle = '#171717';
      ctx.shadowBlur = 0;
      const wheelLen = carLength / 3;
      const wheelW = carLength / 6;
      const wheelOffset = carWidth / 2 + carLength * 0.04;
      const axleOffset = carLength / 3;

      ctx.fillRect(axleOffset - wheelLen / 2, -wheelOffset - wheelW / 2, wheelLen, wheelW);
      ctx.fillRect(axleOffset - wheelLen / 2, wheelOffset - wheelW / 2, wheelLen, wheelW);
      ctx.fillRect(-axleOffset - wheelLen / 2, -wheelOffset - wheelW / 2, wheelLen, wheelW);
      ctx.fillRect(-axleOffset - wheelLen / 2, wheelOffset - wheelW / 2, wheelLen, wheelW);

      ctx.restore();
    }

    // Draw ghost pose while dragging
    if (isDraggingPose && poseStart && poseEnd) {
      const startPos = mapToCanvas(poseStart.x, poseStart.y);
      // Drag angle is in meters space? or pixels?
      // mapToCanvas converts meter coord to pixel coord.
      // The drag points from canvasToMap are in METER coords.
      // So poseStart / poseEnd are meters.
      const dx = poseEnd.x - poseStart.x;
      const dy = poseEnd.y - poseStart.y;
      // Angle in map frame
      const theta = Math.atan2(dy, dx);
      // Visual angle on screen needs rotation
      const visualTheta = theta + rotation * (Math.PI / 180);

      const arrowSize = 25;

      ctx.save();
      ctx.translate(startPos.x, startPos.y);
      // Screen rotation is -visualTheta for standard CCW
      ctx.rotate(-visualTheta);

      // Ghost arrow with mode color
      ctx.fillStyle = MODE_COLORS[mode] + '80'; // 50% opacity
      ctx.strokeStyle = MODE_COLORS[mode];
      ctx.lineWidth = 2;

      ctx.beginPath();
      ctx.moveTo(arrowSize, 0);
      ctx.lineTo(-arrowSize / 2, arrowSize / 2);
      ctx.lineTo(-arrowSize / 2, -arrowSize / 2);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Direction line
      ctx.strokeStyle = MODE_COLORS[mode];
      ctx.lineWidth = 2;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(arrowSize * 2, 0);
      ctx.stroke();

      ctx.restore();
    }
  }, [map, odom, robotMapPose, scale, offset, path, waypoints, isDraggingPose, poseStart, poseEnd, mode, computeFitScale, rotation]);

  // Get cursor style based on mode
  const getCursor = () => {
    if (isDraggingPose) return 'crosshair';
    if (isPanning) return 'grabbing';
    if (mode !== 'none') return 'crosshair';
    return 'grab';
  };

  // Loading state
  // Loading state
  if (!map) {
    return (
      <div className={cn('w-full h-full flex flex-col items-center justify-center bg-muted/5', className)}>
        <Map className="w-12 h-12 text-muted-foreground/20 mb-4" />
        <div className="text-muted-foreground text-sm">Waiting for map data...</div>
        <div className="text-xs text-muted-foreground mt-2 bg-black/20 px-3 py-1 rounded font-mono">
          ros2 launch orbibot_slam slam.launch.py
        </div>
      </div>
    );
  }

  return (
    <div className={cn('relative w-full h-full overflow-hidden bg-muted/5', className)}>
      {/* Canvas Container */}
      <div
        ref={containerRef}
        className={cn(
          'w-full h-full',
          mode !== 'none' && 'ring-2 ring-inset',
        )}
        style={{
          cursor: getCursor(),
          '--tw-ring-color': MODE_COLORS[mode],
        } as React.CSSProperties}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <canvas ref={canvasRef} className="block" style={{ imageRendering: 'pixelated' }} />

        {/* Mode hint overlay */}
        {mode !== 'none' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-black/70 backdrop-blur-md rounded-full text-xs text-white border border-white/10 shadow-lg pointer-events-none z-20">
            Click and drag to set pose orientation
          </div>
        )}
      </div>

      {/* Floating Controls (Bottom Right) */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 z-10">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-card/90 backdrop-blur border shadow-sm rounded-lg hover:bg-accent transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-card/90 backdrop-blur border shadow-sm rounded-lg hover:bg-accent transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleReset}
          className="p-2 bg-card/90 backdrop-blur border shadow-sm rounded-lg hover:bg-accent transition-colors"
          title="Reset View"
        >
          <Maximize2 className="w-4 h-4" />
        </button>

        <div className="h-px bg-border my-1" />

        <button
          onClick={() => setTrackUp(!trackUp)}
          className={cn(
            "p-2 backdrop-blur border shadow-sm rounded-lg transition-colors",
            trackUp ? "bg-primary text-primary-foreground border-primary" : "bg-card/90 hover:bg-accent"
          )}
          title="Track Up Mode"
        >
          <Lock className="w-4 h-4" />
        </button>

        {!trackUp && (
          <div className="flex flex-col items-center bg-card/90 backdrop-blur border shadow-sm rounded-lg p-2 gap-1">
            <RotateCw className="w-3 h-3 text-muted-foreground" />
            <input
              type="range"
              min="-180"
              max="180"
              value={rotation}
              onChange={(e) => setRotation(Number(e.target.value))}
              className="h-24 w-1 bg-muted/50 rounded-lg appearance-none cursor-pointer writing-vertical-lr"
              style={{ writingMode: 'vertical-lr', WebkitAppearance: 'slider-vertical' }}
            />
            <span className="text-[10px] w-6 text-center font-mono">{rotation}°</span>
          </div>
        )}
      </div>

      {/* Map Info Overlay (Bottom Left) */}
      <div className="absolute bottom-4 left-4 pointer-events-none z-10">
        <div className="bg-black/40 backdrop-blur-sm p-2 rounded-lg border border-white/5 text-[10px] space-y-1 text-muted-foreground">
          <div className="flex items-center justify-between gap-4">
            <span>Res:</span> <span className="font-mono text-foreground">{map.info.resolution.toFixed(3)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span>Size:</span> <span className="font-mono text-foreground">{map.info.width}×{map.info.height}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span>Scale:</span> <span className="font-mono text-foreground">{(scale * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

    </div>
  );
}
