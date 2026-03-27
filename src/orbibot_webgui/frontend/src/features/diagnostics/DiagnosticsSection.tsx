/**
 * DiagnosticsSection - Reusable section wrapper for diagnostics page tabs.
 */

import { cn } from '@/lib/utils';

interface DiagnosticsSectionProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export function DiagnosticsSection({ title, icon: Icon, children, className, action }: DiagnosticsSectionProps) {
  return (
    <section className={cn('rounded-xl border border-border bg-card/50 overflow-hidden', className)}>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted/30">
        <Icon className="w-5 h-5 text-primary" />
        <h2 className="text-base font-semibold">{title}</h2>
        {action && <div className="ml-auto">{action}</div>}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}
