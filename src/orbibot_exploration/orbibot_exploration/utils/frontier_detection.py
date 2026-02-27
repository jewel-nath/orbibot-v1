#!/usr/bin/env python3
"""
frontier_detection.py - Frontier detection utilities for autonomous exploration

Implements BFS-based frontier detection algorithm based on m-explore-ros2.

Frontier Definition:
    A frontier cell is an unknown cell (-1) that has at least one
    free cell neighbor (0) in its 4-connected neighborhood.

Algorithm:
    1. Start BFS from robot position on free cells
    2. For each cell, check if neighbors are frontier cells
    3. Build frontier clusters using 8-connected BFS
    4. Filter by minimum size and calculate properties
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from collections import deque
import numpy as np


# OccupancyGrid cell values
FREE_SPACE = 0
UNKNOWN = -1
OCCUPIED = 100


@dataclass
class Frontier:
    """Represents a detected frontier region."""

    # Centroid of the frontier in world coordinates
    centroid_x: float = 0.0
    centroid_y: float = 0.0

    # Closest point to robot in world coordinates (navigation target)
    closest_x: float = 0.0
    closest_y: float = 0.0

    # Initial contact point (first detected cell)
    initial_x: float = 0.0
    initial_y: float = 0.0

    # Number of cells in frontier
    size: int = 0

    # Minimum distance from robot to any frontier cell
    min_distance: float = float('inf')

    # Calculated cost for frontier selection
    cost: float = 0.0

    # All frontier points in world coordinates (for visualization)
    points: List[Tuple[float, float]] = field(default_factory=list)


def get_neighbors_4(idx: int, width: int, height: int) -> List[int]:
    """
    Get 4-connected neighbors (up, down, left, right).

    Args:
        idx: Linear index in the grid
        width: Grid width
        height: Grid height

    Returns:
        List of valid neighbor indices
    """
    neighbors = []
    row = idx // width
    col = idx % width

    # Up
    if row > 0:
        neighbors.append(idx - width)
    # Down
    if row < height - 1:
        neighbors.append(idx + width)
    # Left
    if col > 0:
        neighbors.append(idx - 1)
    # Right
    if col < width - 1:
        neighbors.append(idx + 1)

    return neighbors


def get_neighbors_8(idx: int, width: int, height: int) -> List[int]:
    """
    Get 8-connected neighbors (including diagonals).

    Args:
        idx: Linear index in the grid
        width: Grid width
        height: Grid height

    Returns:
        List of valid neighbor indices
    """
    neighbors = []
    row = idx // width
    col = idx % width

    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            new_row = row + dr
            new_col = col + dc
            if 0 <= new_row < height and 0 <= new_col < width:
                neighbors.append(new_row * width + new_col)

    return neighbors


def index_to_world(
    idx: int,
    width: int,
    resolution: float,
    origin_x: float,
    origin_y: float
) -> Tuple[float, float]:
    """
    Convert grid index to world coordinates.

    Args:
        idx: Linear index in the grid
        width: Grid width
        resolution: Map resolution (meters/cell)
        origin_x: Map origin X
        origin_y: Map origin Y

    Returns:
        Tuple of (world_x, world_y)
    """
    row = idx // width
    col = idx % width
    world_x = col * resolution + origin_x + resolution / 2.0
    world_y = row * resolution + origin_y + resolution / 2.0
    return world_x, world_y


def world_to_index(
    x: float,
    y: float,
    width: int,
    resolution: float,
    origin_x: float,
    origin_y: float
) -> Optional[int]:
    """
    Convert world coordinates to grid index.

    Args:
        x: World X coordinate
        y: World Y coordinate
        width: Grid width
        resolution: Map resolution (meters/cell)
        origin_x: Map origin X
        origin_y: Map origin Y

    Returns:
        Linear index or None if out of bounds
    """
    col = int((x - origin_x) / resolution)
    row = int((y - origin_y) / resolution)
    if col < 0 or row < 0:
        return None
    return row * width + col


def is_frontier_cell(
    idx: int,
    map_data: np.ndarray,
    width: int,
    height: int
) -> bool:
    """
    Check if a cell is a frontier cell.

    A frontier cell is unknown (-1) and has at least one free neighbor (0).

    Args:
        idx: Cell index
        map_data: Flattened occupancy grid data
        width: Grid width
        height: Grid height

    Returns:
        True if the cell is a frontier cell
    """
    if map_data[idx] != UNKNOWN:
        return False

    for nbr in get_neighbors_4(idx, width, height):
        if map_data[nbr] == FREE_SPACE:
            return True

    return False


def build_frontier(
    initial_cell: int,
    reference_x: float,
    reference_y: float,
    map_data: np.ndarray,
    frontier_flag: np.ndarray,
    width: int,
    height: int,
    resolution: float,
    origin_x: float,
    origin_y: float
) -> Frontier:
    """
    Build a frontier cluster starting from an initial frontier cell.

    Uses 8-connected BFS to find all connected frontier cells.

    Args:
        initial_cell: Starting frontier cell index
        reference_x: Robot X position (for distance calculation)
        reference_y: Robot Y position
        map_data: Flattened occupancy grid data
        frontier_flag: Array tracking which cells are already in a frontier
        width: Grid width
        height: Grid height
        resolution: Map resolution
        origin_x: Map origin X
        origin_y: Map origin Y

    Returns:
        Frontier object with computed properties
    """
    frontier = Frontier()

    # Record initial contact point
    ix, iy = index_to_world(initial_cell, width, resolution, origin_x, origin_y)
    frontier.initial_x = ix
    frontier.initial_y = iy

    # BFS to find all connected frontier cells
    queue = deque([initial_cell])
    frontier_flag[initial_cell] = True

    sum_x = 0.0
    sum_y = 0.0

    while queue:
        idx = queue.popleft()

        # Check 8-connected neighbors for more frontier cells
        for nbr in get_neighbors_8(idx, width, height):
            if not frontier_flag[nbr] and is_frontier_cell(nbr, map_data, width, height):
                frontier_flag[nbr] = True
                queue.append(nbr)

                # Convert to world coordinates
                wx, wy = index_to_world(nbr, width, resolution, origin_x, origin_y)
                frontier.points.append((wx, wy))

                # Update size and centroid sum
                frontier.size += 1
                sum_x += wx
                sum_y += wy

                # Update minimum distance to robot
                distance = np.sqrt((reference_x - wx) ** 2 + (reference_y - wy) ** 2)
                if distance < frontier.min_distance:
                    frontier.min_distance = distance
                    frontier.closest_x = wx
                    frontier.closest_y = wy

    # Add initial cell to frontier
    frontier.points.append((ix, iy))
    frontier.size += 1
    sum_x += ix
    sum_y += iy

    # Check distance for initial cell
    distance = np.sqrt((reference_x - ix) ** 2 + (reference_y - iy) ** 2)
    if distance < frontier.min_distance:
        frontier.min_distance = distance
        frontier.closest_x = ix
        frontier.closest_y = iy

    # Calculate centroid
    if frontier.size > 0:
        frontier.centroid_x = sum_x / frontier.size
        frontier.centroid_y = sum_y / frontier.size

    return frontier


def find_nearest_free_cell(
    start_idx: int,
    map_data: np.ndarray,
    width: int,
    height: int,
    max_search: int = 1000
) -> Optional[int]:
    """
    Find the nearest free cell to a given position using BFS.

    Args:
        start_idx: Starting cell index
        map_data: Flattened occupancy grid data
        width: Grid width
        height: Grid height
        max_search: Maximum cells to search

    Returns:
        Index of nearest free cell or None
    """
    if map_data[start_idx] == FREE_SPACE:
        return start_idx

    visited = set()
    queue = deque([start_idx])
    visited.add(start_idx)
    count = 0

    while queue and count < max_search:
        idx = queue.popleft()
        count += 1

        if map_data[idx] == FREE_SPACE:
            return idx

        for nbr in get_neighbors_4(idx, width, height):
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)

    return None


def search_frontiers(
    robot_x: float,
    robot_y: float,
    map_data: np.ndarray,
    width: int,
    height: int,
    resolution: float,
    origin_x: float,
    origin_y: float,
    min_frontier_size: float,
    potential_scale: float,
    gain_scale: float
) -> List[Frontier]:
    """
    Search for frontiers using BFS from robot position.

    This is the main frontier detection function based on m-explore-ros2 algorithm.

    Args:
        robot_x: Robot X position in world coordinates
        robot_y: Robot Y position in world coordinates
        map_data: Flattened occupancy grid data (1D array)
        width: Grid width
        height: Grid height
        resolution: Map resolution (meters/cell)
        origin_x: Map origin X
        origin_y: Map origin Y
        min_frontier_size: Minimum frontier size in meters
        potential_scale: Distance weight for cost calculation
        gain_scale: Size weight for cost calculation

    Returns:
        List of Frontier objects sorted by cost (lowest first)
    """
    frontiers = []

    # Convert robot position to grid index
    robot_idx = world_to_index(robot_x, robot_y, width, resolution, origin_x, origin_y)

    if robot_idx is None or robot_idx < 0 or robot_idx >= len(map_data):
        return frontiers

    # Find nearest free cell to start search
    start_idx = find_nearest_free_cell(robot_idx, map_data, width, height)
    if start_idx is None:
        return frontiers

    # Initialize tracking arrays
    visited = np.zeros(len(map_data), dtype=bool)
    frontier_flag = np.zeros(len(map_data), dtype=bool)

    # BFS from robot position
    queue = deque([start_idx])
    visited[start_idx] = True

    while queue:
        idx = queue.popleft()

        # Check 4-connected neighbors
        for nbr in get_neighbors_4(idx, width, height):
            if visited[nbr]:
                continue

            # If neighbor is free or less occupied, add to BFS queue
            if map_data[nbr] == FREE_SPACE or (
                map_data[nbr] >= 0 and map_data[nbr] <= map_data[idx]
            ):
                visited[nbr] = True
                queue.append(nbr)

            # Check if neighbor is a new frontier cell
            elif not frontier_flag[nbr] and is_frontier_cell(nbr, map_data, width, height):
                frontier_flag[nbr] = True

                # Build the full frontier cluster
                frontier = build_frontier(
                    nbr, robot_x, robot_y, map_data, frontier_flag,
                    width, height, resolution, origin_x, origin_y
                )

                # Filter by minimum size
                frontier_size_meters = frontier.size * resolution
                if frontier_size_meters >= min_frontier_size:
                    # Calculate cost: prefer closer and larger frontiers
                    frontier.cost = (
                        potential_scale * frontier.min_distance -
                        gain_scale * frontier_size_meters
                    )
                    frontiers.append(frontier)

    # Sort by cost (lower is better)
    frontiers.sort(key=lambda f: f.cost)

    return frontiers
