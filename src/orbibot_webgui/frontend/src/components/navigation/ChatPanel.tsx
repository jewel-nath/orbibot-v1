/**
 * ChatPanel — AI chat interface for OrbiBot.
 *
 * Lives inside MissionControl tabs. Sends natural language to
 * the chat_server HTTP API and displays streaming responses.
 *
 * Layout: header → quick actions → messages (scrolls) → input (sticky)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Trash2,
  Bot,
  User,
  Loader2,
  Wrench,
  ChevronDown,
  ChevronRight,
  Battery,
  Compass,
  MapPin,
  Zap,
  Activity,
  Stethoscope,
  WifiOff,
  Square,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useChat } from '@/hooks/useChat';
import type { ChatMessage, ToolCallInfo } from '@/hooks/useChat';
import { useSettings } from '@/contexts/SettingsContext';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  className?: string;
}

const QUICK_ACTIONS = [
  { label: 'Battery?', icon: Battery, message: "What's the battery level?" },
  { label: 'Where?', icon: MapPin, message: 'Where are you right now?' },
  { label: 'IMU', icon: Compass, message: 'Show me the IMU data' },
  { label: 'Status', icon: Zap, message: "What's the system status?" },
  { label: 'Health', icon: Activity, message: 'Run a full health check' },
  { label: 'Diagnostics', icon: Stethoscope, message: 'Check ROS diagnostics and report any issues' },
];

function formatTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function ChatPanel({ className }: ChatPanelProps) {
  const { settings } = useSettings();
  const chatApiBase = settings.chatApiUrl;
  const {
    messages, isLoading, error, connected,
    selectedProvider, setSelectedProvider,
    sendMessage, resetChat, cancel, checkConnection,
  } = useChat();

  const [input, setInput] = useState('');
  const [providers, setProviders] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch providers on mount / when URL changes
  useEffect(() => {
    fetch(`${chatApiBase}/api/providers`)
      .then(r => r.json())
      .then(d => setProviders(d.providers || []))
      .catch(() => setProviders([]));
    checkConnection();
  }, [checkConnection, chatApiBase]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea
  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 96)}px`; // max ~4 rows
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input.trim());
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleQuickAction = (message: string) => {
    if (isLoading) return;
    sendMessage(message);
  };

  return (
    <div className={cn('flex flex-col min-h-0', className)}>
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="shrink-0 flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Bot className="w-5 h-5 text-primary" />
            <span
              className={cn(
                'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-background',
                connected ? 'bg-green-500' : 'bg-destructive',
              )}
            />
          </div>
          <h3 className="font-semibold text-sm">OrbiBot AI</h3>
          {!connected && (
            <button
              onClick={checkConnection}
              className="flex items-center gap-1 text-xs text-destructive hover:underline"
              title="Chat server offline — click to retry"
            >
              <WifiOff className="w-3 h-3" />
              <span>Offline</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <select
            value={selectedProvider ?? ''}
            onChange={e => setSelectedProvider(e.target.value || null)}
            disabled={isLoading}
            className="text-xs border rounded px-1.5 py-0.5 bg-background disabled:opacity-50 max-w-[90px]"
            title="Select LLM provider"
          >
            <option value="">Default</option>
            {providers.map(p => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>

          <button
            onClick={resetChat}
            disabled={isLoading}
            className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-50"
            title="New conversation"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Quick actions ──────────────────────────────────── */}
      <div className="shrink-0 mb-2">
        <div className="grid grid-cols-3 gap-1">
          {QUICK_ACTIONS.map(action => (
            <button
              key={action.label}
              onClick={() => handleQuickAction(action.message)}
              disabled={isLoading || !connected}
              className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-xs border hover:bg-muted/50 transition-colors disabled:opacity-50 truncate"
            >
              <action.icon className="w-3 h-3 text-primary shrink-0" />
              <span className="truncate">{action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Error banner ───────────────────────────────────── */}
      {error && (
        <div className="shrink-0 mb-2 p-2 text-xs text-destructive bg-destructive/10 rounded border border-destructive/20 flex items-center justify-between">
          <span className="truncate">{error}</span>
          <button onClick={checkConnection} className="ml-2 shrink-0 hover:underline">Retry</button>
        </div>
      )}

      {/* ── Messages ───────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 mb-2 pr-0.5">
        {messages.length === 0 ? (
          <EmptyState connected={connected} />
        ) : (
          messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
        )}

        {isLoading && !messages.some(m => m.role === 'assistant' && m.liveTools !== undefined) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground px-2 py-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Thinking…</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input ──────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="shrink-0 flex items-end gap-1.5">
        <textarea
          ref={textareaRef}
          value={input}
          rows={1}
          onChange={e => { setInput(e.target.value); resizeTextarea(); }}
          onKeyDown={handleKeyDown}
          placeholder={!connected ? 'Chat server offline…' : 'Ask OrbiBot anything… (Enter to send)'}
          disabled={isLoading || !connected}
          className={cn(
            'flex-1 px-3 py-2 rounded-lg text-sm resize-none overflow-hidden leading-5',
            'bg-muted/50 border focus:outline-none focus:ring-1 focus:ring-primary',
            'disabled:opacity-50 placeholder:text-muted-foreground/60',
          )}
        />
        {isLoading ? (
          <button
            type="button"
            onClick={cancel}
            className="p-2 rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors"
            title="Stop generation"
          >
            <Square className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim() || !connected}
            className="p-2 rounded-lg transition-colors bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            title="Send (Enter)"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>

      <p className="shrink-0 text-[10px] text-muted-foreground/50 text-right mt-0.5">
        Shift+Enter for new line
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ connected }: { connected: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-8 text-center gap-3 select-none">
      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
        <Bot className="w-6 h-6 text-primary" />
      </div>
      <div>
        <p className="text-sm font-medium">OrbiBot AI</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {connected
            ? 'Ask me about battery, position, sensor data, or anything robot-related.'
            : 'Chat server is offline. Start orbibot_agent to use this feature.'}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-2', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
          <Bot className="w-3.5 h-3.5 text-primary" />
        </div>
      )}

      <div className={cn('flex flex-col gap-0.5', isUser ? 'items-end' : 'items-start', 'max-w-[85%]')}>
        <div
          className={cn(
            'rounded-lg px-3 py-2 text-sm',
            isUser ? 'bg-primary text-primary-foreground' : 'bg-muted/70 text-foreground',
          )}
        >
          {/* Live tool badges while streaming */}
          {message.liveTools && message.liveTools.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {message.liveTools.map(name => (
                <span
                  key={name}
                  className="inline-flex items-center gap-1 text-xs bg-background/70 rounded px-1.5 py-0.5"
                >
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  {name}
                </span>
              ))}
            </div>
          )}

          {/* Completed tool calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <ToolCallsSummary calls={message.toolCalls} />
          )}

          {/* Content */}
          {isUser ? (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            <div
              className={cn(
                'break-words [&>*]:my-0.5 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0',
                '[&_strong]:font-semibold [&_ul]:list-disc [&_ul]:list-inside [&_ul]:ml-2',
                '[&_ol]:list-decimal [&_ol]:list-inside [&_ol]:ml-2',
                '[&_li]:my-0.5 [&_code]:bg-muted/80 [&_code]:px-1 [&_code]:rounded [&_code]:font-mono [&_code]:text-xs',
                '[&_pre]:bg-muted/80 [&_pre]:p-2 [&_pre]:rounded [&_pre]:overflow-x-auto [&_pre]:text-xs',
                '[&_table]:text-xs [&_table]:border-collapse [&_th]:border [&_th]:px-2 [&_th]:py-1 [&_td]:border [&_td]:px-2 [&_td]:py-1',
                '[&_p]:leading-relaxed',
              )}
            >
              {message.content ? (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              ) : message.liveTools ? (
                <span className="text-muted-foreground italic">Thinking…</span>
              ) : null}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-[10px] text-muted-foreground/50 px-1">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {isUser && (
        <div className="shrink-0 w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center mt-0.5">
          <User className="w-3.5 h-3.5 text-primary" />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tool calls summary (collapsible)
// ---------------------------------------------------------------------------

function ToolCallsSummary({ calls }: { calls: ToolCallInfo[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-1.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Wrench className="w-3 h-3" />
        <span>{calls.length} tool{calls.length > 1 ? 's' : ''} called</span>
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>

      {expanded && (
        <div className="mt-1 space-y-1">
          {calls.map((call, idx) => (
            <div key={idx} className="text-xs bg-background/50 rounded p-1.5 font-mono">
              <span className="text-primary">{call.tool}</span>
              {'('}
              <span className="text-muted-foreground">
                {Object.entries(call.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')}
              </span>
              {')'}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
