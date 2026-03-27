/**
 * SectionHeader - Collapsible section with glass-panel styling.
 * Replaces the repeated "glass-panel header + content" pattern in the left panel.
 * Each section takes up ~28px when collapsed, full height when open.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  icon: React.ElementType;
  title: string;
  /** Optional badge or label shown inline in the header (e.g. fault count, source label) */
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function SectionHeader({
  icon: Icon,
  title,
  badge,
  defaultOpen = true,
  children,
  className,
}: SectionHeaderProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={cn('glass-panel overflow-hidden', className)}>
      <button
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/30 transition-colors text-left"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <Icon className="w-3.5 h-3.5 text-primary shrink-0" />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-foreground/80 flex-1 min-w-0">
          {title}
        </span>
        {badge}
        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        }
      </button>
      {open && (
        <div className="border-t border-border/40 p-3">
          {children}
        </div>
      )}
    </div>
  );
}
