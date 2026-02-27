/**
 * Navigation interaction types for map-based pose setting and waypoint management.
 */

/** Map interaction mode for click handling */
export type InteractionMode = 'none' | 'init_pose' | 'nav_goal' | 'waypoint';

/** Click event with map coordinates and orientation */
export interface MapClickEvent {
  x: number;        // meters in map frame
  y: number;        // meters in map frame
  theta: number;    // orientation in radians
}

/** Saved waypoint for patrol routes */
export interface Waypoint {
  id: string;
  name: string;
  x: number;
  y: number;
  theta: number;
}

/** Path point for rendering planned paths */
export interface PathPoint {
  x: number;
  y: number;
}

/** Navigation goal status from Nav2 */
export type GoalStatus =
  | 'idle'
  | 'navigating'
  | 'succeeded'
  | 'canceled'
  | 'failed';
