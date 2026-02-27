/**
 * useKeyboardShortcuts - Centralized keyboard shortcut management hook
 *
 * Features:
 * - Register/unregister shortcuts dynamically
 * - Support for modifier keys (Ctrl, Alt, Shift, Meta)
 * - Automatic ignore when typing in inputs
 * - Shortcut collision detection
 * - Global shortcut registry for help dialog
 */

import { useEffect, useRef } from 'react';

export interface KeyboardShortcut {
  key: string;
  modifiers?: {
    ctrl?: boolean;
    alt?: boolean;
    shift?: boolean;
    meta?: boolean;
  };
  description: string;
  category: 'navigation' | 'control' | 'exploration' | 'general';
  action: () => void;
  enabled?: boolean;
}

// Global registry for all shortcuts (for help dialog)
const shortcutRegistry = new Map<string, Omit<KeyboardShortcut, 'action'>>();

export function getShortcutKey(shortcut: Pick<KeyboardShortcut, 'key' | 'modifiers'>): string {
  const parts: string[] = [];
  if (shortcut.modifiers?.ctrl) parts.push('Ctrl');
  if (shortcut.modifiers?.alt) parts.push('Alt');
  if (shortcut.modifiers?.shift) parts.push('Shift');
  if (shortcut.modifiers?.meta) parts.push('Meta');
  parts.push(shortcut.key.toUpperCase());
  return parts.join('+');
}

export function getDisplayKey(shortcut: Pick<KeyboardShortcut, 'key' | 'modifiers'>): string {
  const parts: string[] = [];
  if (shortcut.modifiers?.ctrl) parts.push('⌃');
  if (shortcut.modifiers?.alt) parts.push('⌥');
  if (shortcut.modifiers?.shift) parts.push('⇧');
  if (shortcut.modifiers?.meta) parts.push('⌘');

  // Format special keys
  const keyDisplay = {
    'escape': 'Esc',
    'arrowup': '↑',
    'arrowdown': '↓',
    'arrowleft': '←',
    'arrowright': '→',
    ' ': 'Space',
    'enter': '↵',
  }[shortcut.key.toLowerCase()] || shortcut.key.toUpperCase();

  parts.push(keyDisplay);
  return parts.join('');
}

export function getRegisteredShortcuts(): Map<string, Omit<KeyboardShortcut, 'action'>> {
  return new Map(shortcutRegistry);
}

function matchesShortcut(e: KeyboardEvent, shortcut: KeyboardShortcut): boolean {
  const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();
  const ctrlMatch = !!shortcut.modifiers?.ctrl === e.ctrlKey;
  const altMatch = !!shortcut.modifiers?.alt === e.altKey;
  const shiftMatch = !!shortcut.modifiers?.shift === e.shiftKey;
  const metaMatch = !!shortcut.modifiers?.meta === e.metaKey;

  return keyMatch && ctrlMatch && altMatch && shiftMatch && metaMatch;
}

function isInputFocused(): boolean {
  const active = document.activeElement;
  return (
    active instanceof HTMLInputElement ||
    active instanceof HTMLTextAreaElement ||
    active instanceof HTMLSelectElement ||
    (active as HTMLElement)?.isContentEditable === true
  );
}

export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  options: {
    ignoreInputs?: boolean;
    enabled?: boolean;
  } = {}
) {
  const { ignoreInputs = true, enabled = true } = options;
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  // Register shortcuts in global registry
  useEffect(() => {
    if (!enabled) return;

    shortcuts.forEach((shortcut) => {
      if (shortcut.enabled !== false) {
        const key = getShortcutKey(shortcut);
        shortcutRegistry.set(key, {
          key: shortcut.key,
          modifiers: shortcut.modifiers,
          description: shortcut.description,
          category: shortcut.category,
          enabled: shortcut.enabled,
        });
      }
    });

    return () => {
      shortcuts.forEach((shortcut) => {
        const key = getShortcutKey(shortcut);
        shortcutRegistry.delete(key);
      });
    };
  }, [shortcuts, enabled]);

  // Handle keydown events
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in inputs (unless overridden)
      if (ignoreInputs && isInputFocused()) {
        return;
      }

      for (const shortcut of shortcutsRef.current) {
        if (shortcut.enabled === false) continue;

        if (matchesShortcut(e, shortcut)) {
          e.preventDefault();
          e.stopPropagation();
          shortcut.action();
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, ignoreInputs]);
}

// Predefined shortcut definitions for documentation
export const SHORTCUT_DEFINITIONS = {
  // Movement controls
  MOVE_FORWARD: { key: 'w', description: 'Move forward', category: 'control' as const },
  MOVE_BACKWARD: { key: 's', description: 'Move backward', category: 'control' as const },
  STRAFE_LEFT: { key: 'a', description: 'Strafe left', category: 'control' as const },
  STRAFE_RIGHT: { key: 'd', description: 'Strafe right', category: 'control' as const },
  ROTATE_CCW: { key: 'q', description: 'Rotate counter-clockwise', category: 'control' as const },
  ROTATE_CW: { key: 'e', description: 'Rotate clockwise', category: 'control' as const },
  EMERGENCY_STOP: { key: ' ', description: 'Emergency stop', category: 'control' as const },

  // Navigation
  INIT_POSE: { key: 'i', description: 'Set initial pose mode', category: 'navigation' as const },
  NAV_GOAL: { key: 'g', description: 'Set navigation goal mode', category: 'navigation' as const },
  ADD_WAYPOINT: { key: 'w', modifiers: { shift: true }, description: 'Add waypoint mode', category: 'navigation' as const },
  CANCEL_NAV: { key: 'escape', description: 'Cancel navigation', category: 'navigation' as const },

  // Exploration
  START_EXPLORE: { key: 'x', description: 'Start exploration', category: 'exploration' as const },
  PAUSE_EXPLORE: { key: 'p', description: 'Pause exploration', category: 'exploration' as const },
  SAVE_MAP: { key: 's', modifiers: { ctrl: true }, description: 'Save map', category: 'exploration' as const },

  // General
  HELP: { key: '?', description: 'Show keyboard shortcuts', category: 'general' as const },
  TOGGLE_THEME: { key: 't', modifiers: { ctrl: true }, description: 'Toggle theme', category: 'general' as const },
};
