import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface DashboardProps {
  children?: ReactNode;
  className?: string;
}

export function Dashboard({ children, className = '' }: DashboardProps) {
  return (
    <main className={cn(
      'flex-1 overflow-hidden bg-gradient-to-br from-background via-background to-muted/20',
      'p-3 lg:p-4',
      className
    )}>
      <div className="h-full grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4 max-w-[1920px] mx-auto">
        {children}
      </div>
    </main>
  );
}

export function DashboardLeft({ children, className = '' }: DashboardProps) {
  return (
    <div className={cn(
      'lg:col-span-3 flex flex-col gap-3 overflow-y-auto overflow-x-visible',
      'pr-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent',
      className
    )}>
      {children}
    </div>
  );
}

export function DashboardCenter({ children, className = '' }: DashboardProps) {
  return (
    <div className={cn(
      'lg:col-span-6 flex flex-col gap-3 lg:gap-4 overflow-hidden relative',
      'rounded-xl',
      className
    )}>
      {children}
    </div>
  );
}

export function DashboardRight({ children, className = '' }: DashboardProps) {
  return (
    <div className={cn(
      'lg:col-span-3 flex flex-col gap-3 lg:gap-4 overflow-y-auto',
      'pl-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent',
      className
    )}>
      {children}
    </div>
  );
}