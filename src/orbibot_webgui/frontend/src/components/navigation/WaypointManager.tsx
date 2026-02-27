/**
 * WaypointManager - Side panel for managing waypoints and patrol routes
 *
 * Features:
 * - Waypoint list with name editing and deletion
 * - Navigate to individual waypoints
 * - Save/Load waypoints to localStorage
 * - Export/Import waypoints as JSON
 * - Patrol controls with loop toggle
 * - Progress indicator during patrol
 */

import { useState, useRef, useCallback } from 'react';
import {
  MapPin,
  Trash2,
  Play,
  Pause,
  Square,
  Navigation2,
  Save,
  FolderOpen,
  Download,
  Upload,
  Repeat,
  GripVertical,
  Edit2,
  Check,
  X,
  SkipForward,
} from 'lucide-react';
import { useNavigationContext } from '@/contexts/NavigationContext';
import { useNavGoal } from '@/hooks/useNavGoal';
import { useRos } from '@/contexts/RosContext';
import { useWaypointPatrol } from '@/hooks/useWaypointPatrol';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface WaypointManagerProps {
  className?: string;
}

export function WaypointManager({ className }: WaypointManagerProps) {
  const {
    waypoints,
    updateWaypoint,
    removeWaypoint,
    reorderWaypoints,
    clearWaypoints,
    saveWaypoints,
    loadWaypoints,
    exportWaypoints,
    importWaypoints,
    navigationAvailable,
  } = useNavigationContext();

  const { sendGoal } = useNavGoal();
  const { isConnected } = useRos();

  const {
    isPatrolling,
    isPaused,
    currentIndex,
    loop,
    setLoop,
    startPatrol,
    pausePatrol,
    resumePatrol,
    stopPatrol,
    skipToWaypoint,
    progress,
  } = useWaypointPatrol();

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  // Drag state
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  // File input ref for import
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Start editing a waypoint name
  const startEditing = useCallback((id: string, currentName: string) => {
    setEditingId(id);
    setEditName(currentName);
  }, []);

  // Save edited name
  const saveEdit = useCallback(() => {
    if (editingId && editName.trim()) {
      updateWaypoint(editingId, { name: editName.trim() });
    }
    setEditingId(null);
    setEditName('');
  }, [editingId, editName, updateWaypoint]);

  // Cancel editing
  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditName('');
  }, []);

  // Navigate to a specific waypoint
  const navigateToWaypoint = useCallback(
    (index: number) => {
      const wp = waypoints[index];
      if (wp) {
        sendGoal(wp.x, wp.y, wp.theta);
        toast.info(`Navigating to ${wp.name}`);
      }
    },
    [waypoints, sendGoal]
  );

  // Handle drag start
  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index);
  }, []);

  // Handle drag over
  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  }, []);

  // Handle drop
  const handleDrop = useCallback(
    (toIndex: number) => {
      if (dragIndex !== null && dragIndex !== toIndex) {
        reorderWaypoints(dragIndex, toIndex);
      }
      setDragIndex(null);
      setDragOverIndex(null);
    },
    [dragIndex, reorderWaypoints]
  );

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    setDragIndex(null);
    setDragOverIndex(null);
  }, []);

  // Export waypoints to file
  const handleExport = useCallback(() => {
    const json = exportWaypoints();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'orbibot_waypoints.json';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Waypoints exported');
  }, [exportWaypoints]);

  // Import waypoints from file
  const handleImport = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        const json = event.target?.result as string;
        importWaypoints(json);
      };
      reader.readAsText(file);

      // Reset input
      e.target.value = '';
    },
    [importWaypoints]
  );

  return (
    <div className={cn('glass-panel p-4 flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Waypoints</h3>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            {waypoints.length}
          </span>
        </div>
      </div>

      {/* Waypoint List */}
      <div className="flex-1 overflow-y-auto min-h-0 space-y-1 mb-4">
        {waypoints.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            <MapPin className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No waypoints yet</p>
            <p className="text-xs mt-1">
              Press <kbd className="px-1 py-0.5 bg-muted rounded">W</kbd> and click on the map
            </p>
          </div>
        ) : (
          waypoints.map((wp, index) => (
            <div
              key={wp.id}
              draggable={!isPatrolling}
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDrop={() => handleDrop(index)}
              onDragEnd={handleDragEnd}
              className={cn(
                'flex items-center gap-2 p-2 rounded-lg border transition-all',
                'hover:bg-muted/50',
                dragIndex === index && 'opacity-50',
                dragOverIndex === index && 'border-orange-500 border-dashed',
                isPatrolling && currentIndex === index && 'bg-blue-500/10 border-blue-500'
              )}
            >
              {/* Drag handle */}
              <div
                className={cn(
                  'cursor-grab active:cursor-grabbing text-muted-foreground',
                  isPatrolling && 'opacity-30 cursor-not-allowed'
                )}
              >
                <GripVertical className="w-4 h-4" />
              </div>

              {/* Index */}
              <div
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold',
                  'bg-orange-500/20 text-orange-500',
                  isPatrolling && currentIndex === index && 'bg-blue-500 text-white animate-pulse'
                )}
              >
                {index + 1}
              </div>

              {/* Name - editable */}
              {editingId === wp.id ? (
                <div className="flex-1 flex items-center gap-1">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveEdit();
                      if (e.key === 'Escape') cancelEdit();
                    }}
                    className="flex-1 px-2 py-1 text-sm bg-background border rounded"
                    autoFocus
                  />
                  <button
                    onClick={saveEdit}
                    className="p-1 hover:bg-green-500/20 rounded text-green-500"
                  >
                    <Check className="w-3 h-3" />
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="p-1 hover:bg-red-500/20 rounded text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{wp.name}</div>
                  <div className="text-xs text-muted-foreground">
                    ({wp.x.toFixed(2)}, {wp.y.toFixed(2)})
                  </div>
                </div>
              )}

              {/* Actions */}
              {editingId !== wp.id && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => startEditing(wp.id, wp.name)}
                    className="p-1.5 hover:bg-muted rounded transition-colors"
                    title="Edit name"
                    disabled={isPatrolling}
                  >
                    <Edit2 className="w-3 h-3 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => navigateToWaypoint(index)}
                    className="p-1.5 hover:bg-blue-500/20 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    title={!navigationAvailable ? 'Navigation server not running' : 'Navigate here'}
                    disabled={!isConnected || !navigationAvailable || isPatrolling}
                  >
                    <Navigation2 className="w-3 h-3 text-blue-500" />
                  </button>
                  {isPatrolling && currentIndex !== index ? (
                    <button
                      onClick={() => skipToWaypoint(index)}
                      className="p-1.5 hover:bg-orange-500/20 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Skip to this waypoint"
                      disabled={!isConnected || !navigationAvailable}
                    >
                      <SkipForward className="w-3 h-3 text-orange-500" />
                    </button>
                  ) : (
                    <button
                      onClick={() => removeWaypoint(wp.id)}
                      className="p-1.5 hover:bg-red-500/20 rounded transition-colors"
                      title="Delete"
                      disabled={isPatrolling}
                    >
                      <Trash2 className="w-3 h-3 text-red-500" />
                    </button>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Patrol Progress */}
      {isPatrolling && (
        <div className="mb-4 p-3 bg-blue-500/10 rounded-lg border border-blue-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-blue-500">
              {isPaused ? 'Patrol Paused' : 'Patrolling...'}
            </span>
            <span className="text-xs text-muted-foreground">
              {currentIndex + 1} / {waypoints.length}
            </span>
          </div>
          <div className="h-2 bg-blue-500/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Patrol Controls */}
      <div className="space-y-3 pt-3 border-t">
        <div className="flex items-center gap-2">
          {!isPatrolling ? (
            <button
              onClick={startPatrol}
              disabled={waypoints.length === 0 || !isConnected || !navigationAvailable}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg',
                'bg-primary text-primary-foreground font-medium',
                'hover:bg-primary/90 transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              title={!navigationAvailable ? 'Navigation server not running' : ''}
            >
              <Play className="w-4 h-4" />
              Start Patrol
            </button>
          ) : (
            <>
              {isPaused ? (
                <button
                  onClick={resumePatrol}
                  disabled={!isConnected || !navigationAvailable}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="w-4 h-4" />
                  Resume
                </button>
              ) : (
                <button
                  onClick={pausePatrol}
                  disabled={!navigationAvailable}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-yellow-600 text-white font-medium hover:bg-yellow-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Pause className="w-4 h-4" />
                  Pause
                </button>
              )}
              <button
                onClick={stopPatrol}
                disabled={!navigationAvailable}
                className="px-4 py-2 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Square className="w-4 h-4" />
              </button>
            </>
          )}
        </div>

        {/* Loop Toggle */}
        <button
          onClick={() => setLoop(!loop)}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border transition-colors',
            loop
              ? 'bg-primary/10 border-primary text-primary'
              : 'hover:bg-muted/50 text-muted-foreground'
          )}
        >
          <Repeat className="w-4 h-4" />
          Loop: {loop ? 'On' : 'Off'}
        </button>
      </div>

      {/* Save/Load/Import/Export */}
      <div className="mt-3 pt-3 border-t">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={saveWaypoints}
            disabled={waypoints.length === 0}
            className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/50 border transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span className="text-sm">Save</span>
          </button>
          <button
            onClick={loadWaypoints}
            className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/50 border transition-colors"
          >
            <FolderOpen className="w-4 h-4" />
            <span className="text-sm">Load</span>
          </button>
          <button
            onClick={handleExport}
            disabled={waypoints.length === 0}
            className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/50 border transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span className="text-sm">Export</span>
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-muted/50 border transition-colors"
          >
            <Upload className="w-4 h-4" />
            <span className="text-sm">Import</span>
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleImport}
          className="hidden"
        />

        {/* Clear All */}
        {waypoints.length > 0 && !isPatrolling && (
          <button
            onClick={clearWaypoints}
            className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-red-500/10 text-red-500 border border-red-500/30 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span className="text-sm">Clear All</span>
          </button>
        )}
      </div>
    </div>
  );
}
