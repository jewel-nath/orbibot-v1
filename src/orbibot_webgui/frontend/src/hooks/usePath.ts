/**
 * usePath - Hook for accessing the navigation path
 *
 * Returns the path from NavigationContext, which subscribes to /plan topic.
 * Provides convenience methods for path analysis.
 */

import { useMemo } from 'react';
import { useNavigationContext } from '@/contexts/NavigationContext';
import type { PathPoint } from '@/types/interaction';

interface UsePathReturn {
  path: PathPoint[];
  hasPath: boolean;
  pathLength: number;
  startPoint: PathPoint | null;
  endPoint: PathPoint | null;
}

/**
 * Calculate Euclidean distance between two points
 */
function distance(p1: PathPoint, p2: PathPoint): number {
  return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
}

export function usePath(): UsePathReturn {
  const { path } = useNavigationContext();

  const hasPath = path.length > 0;

  const pathLength = useMemo(() => {
    if (path.length < 2) return 0;

    let total = 0;
    for (let i = 1; i < path.length; i++) {
      total += distance(path[i - 1], path[i]);
    }
    return total;
  }, [path]);

  const startPoint = hasPath ? path[0] : null;
  const endPoint = hasPath ? path[path.length - 1] : null;

  return {
    path,
    hasPath,
    pathLength,
    startPoint,
    endPoint,
  };
}
