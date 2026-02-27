/**
 * useTouchGestures - Touch gesture support for mobile devices
 *
 * Features:
 * - Touch start/end for button-like interactions
 * - Swipe detection for directional control
 * - Pinch zoom for map interactions
 * - Multi-touch support
 * - Prevents default touch behaviors (scrolling) when active
 */

import { useCallback, useRef } from 'react';

export interface TouchPoint {
  x: number;
  y: number;
  identifier: number;
  timestamp: number;
}

export interface SwipeGesture {
  direction: 'up' | 'down' | 'left' | 'right';
  distance: number;
  velocity: number;
}

export interface PinchGesture {
  scale: number;
  center: { x: number; y: number };
}

interface UseTouchGesturesOptions {
  onTouchStart?: (point: TouchPoint) => void;
  onTouchEnd?: (point: TouchPoint) => void;
  onSwipe?: (gesture: SwipeGesture) => void;
  onPinch?: (gesture: PinchGesture) => void;
  onMultiTouch?: (points: TouchPoint[]) => void;
  swipeThreshold?: number; // Minimum distance for swipe detection (px)
  swipeVelocityThreshold?: number; // Minimum velocity for swipe (px/ms)
  preventScroll?: boolean;
}

export function useTouchGestures(options: UseTouchGesturesOptions = {}) {
  const {
    onTouchStart,
    onTouchEnd,
    onSwipe,
    onPinch,
    onMultiTouch,
    swipeThreshold = 50,
    swipeVelocityThreshold = 0.3,
    preventScroll = true,
  } = options;

  const touchStartRef = useRef<TouchPoint | null>(null);
  const lastTouchesRef = useRef<TouchPoint[]>([]);
  const initialPinchDistanceRef = useRef<number | null>(null);

  const getTouchPoint = useCallback(
    (touch: Touch, timestamp: number): TouchPoint => ({
      x: touch.clientX,
      y: touch.clientY,
      identifier: touch.identifier,
      timestamp,
    }),
    []
  );

  const getDistance = useCallback((p1: TouchPoint, p2: TouchPoint): number => {
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
  }, []);

  const getCenter = useCallback(
    (p1: TouchPoint, p2: TouchPoint): { x: number; y: number } => ({
      x: (p1.x + p2.x) / 2,
      y: (p1.y + p2.y) / 2,
    }),
    []
  );

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      if (preventScroll) {
        e.preventDefault();
      }

      const timestamp = Date.now();
      const touches = Array.from(e.touches).map((t) =>
        getTouchPoint(t, timestamp)
      );

      if (touches.length === 1) {
        touchStartRef.current = touches[0];
        onTouchStart?.(touches[0]);
      } else if (touches.length === 2) {
        initialPinchDistanceRef.current = getDistance(touches[0], touches[1]);
        onMultiTouch?.(touches);
      }

      lastTouchesRef.current = touches;
    },
    [getTouchPoint, getDistance, onTouchStart, onMultiTouch, preventScroll]
  );

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (preventScroll) {
        e.preventDefault();
      }

      const timestamp = Date.now();
      const touches = Array.from(e.touches).map((t) =>
        getTouchPoint(t, timestamp)
      );

      // Pinch gesture
      if (touches.length === 2 && initialPinchDistanceRef.current !== null) {
        const currentDistance = getDistance(touches[0], touches[1]);
        const scale = currentDistance / initialPinchDistanceRef.current;
        const center = getCenter(touches[0], touches[1]);

        onPinch?.({ scale, center });
      }

      lastTouchesRef.current = touches;
    },
    [getTouchPoint, getDistance, getCenter, onPinch, preventScroll]
  );

  const handleTouchEnd = useCallback(
    (e: TouchEvent) => {
      const timestamp = Date.now();

      // Single touch end - check for swipe
      if (e.changedTouches.length === 1 && touchStartRef.current) {
        const endPoint = getTouchPoint(e.changedTouches[0], timestamp);
        const startPoint = touchStartRef.current;

        const dx = endPoint.x - startPoint.x;
        const dy = endPoint.y - startPoint.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const duration = timestamp - startPoint.timestamp;
        const velocity = distance / duration;

        onTouchEnd?.(endPoint);

        // Check for swipe gesture
        if (
          distance >= swipeThreshold &&
          velocity >= swipeVelocityThreshold
        ) {
          const absX = Math.abs(dx);
          const absY = Math.abs(dy);
          let direction: SwipeGesture['direction'];

          if (absX > absY) {
            direction = dx > 0 ? 'right' : 'left';
          } else {
            direction = dy > 0 ? 'down' : 'up';
          }

          onSwipe?.({ direction, distance, velocity });
        }

        touchStartRef.current = null;
      }

      // Reset pinch on multi-touch end
      if (e.touches.length < 2) {
        initialPinchDistanceRef.current = null;
      }
    },
    [getTouchPoint, onTouchEnd, onSwipe, swipeThreshold, swipeVelocityThreshold]
  );

  // Return handlers to attach to elements
  const touchHandlers = {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
    onTouchCancel: handleTouchEnd,
  };

  // Also return a ref-based approach for DOM elements
  const bindTouch = useCallback(
    (element: HTMLElement | null) => {
      if (!element) return;

      element.addEventListener('touchstart', handleTouchStart, {
        passive: !preventScroll,
      });
      element.addEventListener('touchmove', handleTouchMove, {
        passive: !preventScroll,
      });
      element.addEventListener('touchend', handleTouchEnd);
      element.addEventListener('touchcancel', handleTouchEnd);

      return () => {
        element.removeEventListener('touchstart', handleTouchStart);
        element.removeEventListener('touchmove', handleTouchMove);
        element.removeEventListener('touchend', handleTouchEnd);
        element.removeEventListener('touchcancel', handleTouchEnd);
      };
    },
    [handleTouchStart, handleTouchMove, handleTouchEnd, preventScroll]
  );

  return { touchHandlers, bindTouch };
}

/**
 * Hook for simple touch-hold button behavior
 */
export function useTouchButton(options: {
  onPress?: () => void;
  onRelease?: () => void;
  disabled?: boolean;
}) {
  const { onPress, onRelease, disabled = false } = options;
  const isPressedRef = useRef(false);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent | TouchEvent) => {
      if (disabled) return;
      e.preventDefault();
      if (!isPressedRef.current) {
        isPressedRef.current = true;
        onPress?.();
      }
    },
    [disabled, onPress]
  );

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent | TouchEvent) => {
      if (disabled) return;
      e.preventDefault();
      if (isPressedRef.current) {
        isPressedRef.current = false;
        onRelease?.();
      }
    },
    [disabled, onRelease]
  );

  const handleMouseDown = useCallback(
    (_e: React.MouseEvent | MouseEvent) => {
      if (disabled) return;
      if (!isPressedRef.current) {
        isPressedRef.current = true;
        onPress?.();
      }
    },
    [disabled, onPress]
  );

  const handleMouseUp = useCallback(
    (_e: React.MouseEvent | MouseEvent) => {
      if (disabled) return;
      if (isPressedRef.current) {
        isPressedRef.current = false;
        onRelease?.();
      }
    },
    [disabled, onRelease]
  );

  const handleMouseLeave = useCallback(() => {
    if (isPressedRef.current) {
      isPressedRef.current = false;
      onRelease?.();
    }
  }, [onRelease]);

  return {
    onTouchStart: handleTouchStart,
    onTouchEnd: handleTouchEnd,
    onTouchCancel: handleTouchEnd,
    onMouseDown: handleMouseDown,
    onMouseUp: handleMouseUp,
    onMouseLeave: handleMouseLeave,
  };
}

/**
 * Hook for virtual joystick control
 */
export function useVirtualJoystick(options: {
  onMove?: (x: number, y: number) => void;
  onRelease?: () => void;
  maxDistance?: number;
  deadzone?: number;
}) {
  const { onMove, onRelease, maxDistance = 50, deadzone = 5 } = options;

  const centerRef = useRef<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLElement | null>(null);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    e.preventDefault();
    const touch = e.touches[0];
    centerRef.current = { x: touch.clientX, y: touch.clientY };
  }, []);

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      e.preventDefault();
      if (!centerRef.current) return;

      const touch = e.touches[0];
      let dx = touch.clientX - centerRef.current.x;
      let dy = touch.clientY - centerRef.current.y;

      // Apply deadzone
      const distance = Math.sqrt(dx * dx + dy * dy);
      if (distance < deadzone) {
        onMove?.(0, 0);
        return;
      }

      // Clamp to max distance and normalize to -1 to 1
      if (distance > maxDistance) {
        dx = (dx / distance) * maxDistance;
        dy = (dy / distance) * maxDistance;
      }

      const normalizedX = dx / maxDistance;
      const normalizedY = -dy / maxDistance; // Invert Y for typical coordinate system

      onMove?.(normalizedX, normalizedY);
    },
    [maxDistance, deadzone, onMove]
  );

  const handleTouchEnd = useCallback(() => {
    centerRef.current = null;
    onRelease?.();
  }, [onRelease]);

  const bindJoystick = useCallback(
    (element: HTMLElement | null) => {
      if (!element) return;
      containerRef.current = element;

      element.addEventListener('touchstart', handleTouchStart, {
        passive: false,
      });
      element.addEventListener('touchmove', handleTouchMove, {
        passive: false,
      });
      element.addEventListener('touchend', handleTouchEnd);
      element.addEventListener('touchcancel', handleTouchEnd);

      return () => {
        element.removeEventListener('touchstart', handleTouchStart);
        element.removeEventListener('touchmove', handleTouchMove);
        element.removeEventListener('touchend', handleTouchEnd);
        element.removeEventListener('touchcancel', handleTouchEnd);
      };
    },
    [handleTouchStart, handleTouchMove, handleTouchEnd]
  );

  return { bindJoystick };
}
