/**
 * ChatPanel — AI chat interface for OrbiBot.
 *
 * Lives inside the MissionControl right-panel tabs alongside
 * Control, Patrol, and Explore.  Sends natural language to
 * the chat_server HTTP API and displays responses.
 */

import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Trash2,
  Bot,
  User,
  Loader2,
  Wrench,
  ChevronDown,
  ChevronRight,
  Zap,
  Battery,
  Compass,
  MapPin,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useChat } from '@/hooks/useChat';
import type { ChatMessage, ToolCallInfo } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  className?: string;
}

// Quick action buttons the user can tap instead of typing
const QUICK_ACTIONS = [
  { label: 'Battery?', icon: Battery, message: "What's the battery level?" },
  { label: 'Where?', icon: MapPin, message: 'Where are you right now?' },
  { label: 'IMU', icon: Compass, message: 'Show me the IMU data' },
  { label: 'Status', icon: Zap, message: "What's the system status?" },
];

export function ChatPanel({ className }: ChatPanelProps) {
  const { messages, isLoading, sendMessage, resetChat } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  const handleQuickAction = (message: string) => {
    if (isLoading) return;
    sendMessage(message);
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-sm">OrbiBot AI</h3>
        </div>
        <button
          onClick={resetChat}
          className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          title="New conversation"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Quick actions — shown when conversation is empty */}
      {messages.length === 0 && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-2">Quick actions</p>
          <div className="grid grid-cols-2 gap-1.5">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => handleQuickAction(action.message)}
                disabled={isLoading}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs',
                  'border hover:bg-muted/50 transition-colors',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                <action.icon className="w-3 h-3 text-primary" />
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0 mb-2">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground px-2 py-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex items-center gap-1.5">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask OrbiBot..."
          disabled={isLoading}
          className={cn(
            'flex-1 px-3 py-2 rounded-lg text-sm',
            'bg-muted/50 border focus:outline-none focus:ring-1 focus:ring-primary',
            'disabled:opacity-50',
            'placeholder:text-muted-foreground/60'
          )}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className={cn(
            'p-2 rounded-lg transition-colors',
            'bg-primary text-primary-foreground',
            'hover:bg-primary/90',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-2', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5">
          <Bot className="w-3.5 h-3.5 text-primary" />
        </div>
      )}

      <div
        className={cn(
          'max-w-[85%] rounded-lg px-3 py-2 text-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted/70 text-foreground'
        )}
      >
        {/* Tool calls (collapsible) */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallsSummary calls={message.toolCalls} />
        )}

        {/* Message text: plain for user, markdown for assistant */}
        {isUser ? (
          <div className="whitespace-pre-wrap break-words">{message.content}</div>
        ) : (
          <div
            className={cn(
              'break-words [&>*]:my-0.5 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0',
              '[&_strong]:font-semibold [&_ul]:list-disc [&_ul]:list-inside [&_ul]:ml-2',
              '[&_li]:my-0.5 [&_code]:bg-muted/80 [&_code]:px-1 [&_code]:rounded [&_code]:font-mono [&_code]:text-xs'
            )}
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center mt-0.5">
          <User className="w-3.5 h-3.5 text-primary" />
        </div>
      )}
    </div>
  );
}

function ToolCallsSummary({ calls }: { calls: ToolCallInfo[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-1.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Wrench className="w-3 h-3" />
        <span>
          {calls.length} tool{calls.length > 1 ? 's' : ''} called
        </span>
        {expanded ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
      </button>

      {expanded && (
        <div className="mt-1 space-y-1">
          {calls.map((call, idx) => (
            <div
              key={idx}
              className="text-xs bg-background/50 rounded p-1.5 font-mono"
            >
              <span className="text-primary">{call.tool}</span>
              {'('}
              <span className="text-muted-foreground">
                {Object.entries(call.args)
                  .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                  .join(', ')}
              </span>
              {')'}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
