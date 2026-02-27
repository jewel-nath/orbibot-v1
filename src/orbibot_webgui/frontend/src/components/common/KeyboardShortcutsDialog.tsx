/**
 * KeyboardShortcutsDialog - Modal showing all available keyboard shortcuts
 *
 * Features:
 * - Opens with ? key
 * - Groups shortcuts by category
 * - Shows key combinations with visual styling
 * - Closable with Escape or clicking outside
 */

import { useState, useEffect, useCallback } from 'react';
import { X, Keyboard } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useKeyboardShortcuts,
  getDisplayKey,
} from '@/hooks/useKeyboardShortcuts';

interface KeyboardShortcutsDialogProps {
  className?: string;
}

interface ShortcutItem {
  key: string;
  modifiers?: {
    ctrl?: boolean;
    alt?: boolean;
    shift?: boolean;
    meta?: boolean;
  };
  description: string;
}

interface ShortcutCategory {
  title: string;
  shortcuts: ShortcutItem[];
}

// All shortcuts organized by category
const SHORTCUT_CATEGORIES: ShortcutCategory[] = [
  {
    title: 'Robot Control',
    shortcuts: [
      { key: 'w', description: 'Move forward' },
      { key: 's', description: 'Move backward' },
      { key: 'a', description: 'Strafe left' },
      { key: 'd', description: 'Strafe right' },
      { key: 'q', description: 'Rotate CCW' },
      { key: 'e', description: 'Rotate CW' },
      { key: ' ', description: 'Emergency stop' },
      { key: '1-9', description: 'Set speed 10-90%' },
    ],
  },
  {
    title: 'Navigation',
    shortcuts: [
      { key: 'i', description: 'Initial pose mode' },
      { key: 'g', description: 'Navigation goal mode' },
      { key: 'w', modifiers: { shift: true }, description: 'Waypoint mode' },
      { key: 'escape', description: 'Cancel / Exit mode' },
    ],
  },
  {
    title: 'Exploration',
    shortcuts: [
      { key: 'x', description: 'Toggle exploration (start/pause)' },
      { key: 'escape', description: 'Stop exploration' },
      { key: 's', modifiers: { ctrl: true }, description: 'Save map' },
    ],
  },
  {
    title: 'General',
    shortcuts: [
      { key: '?', description: 'Show shortcuts' },
      { key: 't', modifiers: { ctrl: true }, description: 'Toggle theme' },
    ],
  },
];

function ShortcutKey({ shortcut }: { shortcut: ShortcutItem }) {
  const displayKey = getDisplayKey(shortcut);

  // Handle special display for range keys like "1-9"
  if (shortcut.key.includes('-')) {
    return (
      <kbd className="px-2 py-1 text-xs font-mono bg-muted border rounded shadow-sm">
        {shortcut.key}
      </kbd>
    );
  }

  return (
    <kbd className="px-2 py-1 text-xs font-mono bg-muted border rounded shadow-sm">
      {displayKey}
    </kbd>
  );
}

export function KeyboardShortcutsDialog({ className }: KeyboardShortcutsDialogProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Open dialog with ? key
  useKeyboardShortcuts(
    [
      {
        key: '?',
        description: 'Show keyboard shortcuts',
        category: 'general',
        action: () => setIsOpen(true),
      },
    ],
    { enabled: !isOpen }
  );

  // Close with Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Handle backdrop click
  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setIsOpen(false);
    }
  }, []);

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center',
        'bg-black/50 backdrop-blur-sm',
        className
      )}
      onClick={handleBackdropClick}
    >
      <div
        className={cn(
          'relative w-full max-w-2xl max-h-[80vh] overflow-auto',
          'bg-card border rounded-xl shadow-2xl',
          'm-4 p-6'
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Keyboard className="w-6 h-6 text-primary" />
            <h2 id="shortcuts-title" className="text-xl font-semibold">
              Keyboard Shortcuts
            </h2>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Shortcut Categories */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {SHORTCUT_CATEGORIES.map((category) => (
            <div key={category.title}>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3">
                {category.title}
              </h3>
              <div className="space-y-2">
                {category.shortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-1.5 px-3 bg-muted/30 rounded-lg"
                  >
                    <span className="text-sm">{shortcut.description}</span>
                    <ShortcutKey shortcut={shortcut} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer hint */}
        <div className="mt-6 pt-4 border-t text-center">
          <p className="text-xs text-muted-foreground">
            Press <kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">Esc</kbd> to close
          </p>
        </div>
      </div>
    </div>
  );
}
