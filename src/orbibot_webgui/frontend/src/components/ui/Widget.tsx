
import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Loader2, AlertCircle } from 'lucide-react';

interface WidgetAction {
    icon: React.ElementType;
    onClick: () => void;
    label: string;
}

interface WidgetProps {
    title: string;
    icon?: React.ElementType;
    children: ReactNode;
    className?: string;
    actions?: WidgetAction[];
    loading?: boolean;
    error?: string | null;
    empty?: boolean;
    emptyMessage?: string;
}

export function Widget({
    title,
    icon: Icon,
    children,
    className,
    actions,
    loading = false,
    error = null,
    empty = false,
    emptyMessage = "No data available",
}: WidgetProps) {
    return (
        <div className={cn("glass-panel flex flex-col overflow-hidden", className)}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-card/30 backdrop-blur-sm">
                <div className="flex items-center gap-2.5">
                    {Icon && <Icon className="w-4 h-4 text-primary" />}
                    <h3 className="text-sm font-semibold tracking-wide text-foreground/90 uppercase">{title}</h3>
                </div>

                {actions && actions.length > 0 && (
                    <div className="flex items-center gap-1">
                        {actions.map((action, idx) => (
                            <button
                                key={idx}
                                onClick={action.onClick}
                                className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                                title={action.label}
                            >
                                <action.icon className="w-4 h-4" />
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Content Area */}
            <div className="flex-1 relative p-4 overflow-auto">
                {loading ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/50 backdrop-blur-[2px] z-10">
                        <Loader2 className="w-8 h-8 text-primary animate-spin mb-2" />
                        <span className="text-xs text-muted-foreground font-medium animate-pulse">Loading data...</span>
                    </div>
                ) : error ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-4">
                        <AlertCircle className="w-8 h-8 text-destructive mb-2 opacity-80" />
                        <p className="text-sm font-medium text-destructive">{error}</p>
                    </div>
                ) : empty ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-4">
                        <div className="w-12 h-12 rounded-full bg-muted/30 flex items-center justify-center mb-3">
                            {Icon ? <Icon className="w-6 h-6 text-muted-foreground/40" /> : <Loader2 className="w-6 h-6 text-muted-foreground/40" />}
                        </div>
                        <p className="text-sm text-muted-foreground">{emptyMessage}</p>
                    </div>
                ) : (
                    children
                )}
            </div>
        </div>
    );
}
