/**
 * ChatPanel — AI chat interface for OrbiBot.
 *
 * Lives inside the MissionControl right-panel tabs alongside
 * Control, Patrol, and Explore.  Sends natural language to
 * the chat_server HTTP API and displays responses.
 *
 * Features:
 *   - SSE streaming with live tool badges
 *   - Provider selector (Gemini, Claude, Kimi, Ollama)
 *   - RobotTester mode with nav action buttons
 *   - Test suite runner with pass/fail display
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
  Play,
  Square,
  RotateCcw,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useChat } from '@/hooks/useChat';
import type { ChatMessage, ToolCallInfo, ChatMode } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  className?: string;
}

// Chat server lives on the same host, different port
const CHAT_API_BASE = `http://${window.location.hostname}:8082`;

// Quick action buttons the user can tap instead of typing
const QUICK_ACTIONS = [
  { label: 'Battery?', icon: Battery, message: "What's the battery level?" },
  { label: 'Where?', icon: MapPin, message: 'Where are you right now?' },
  { label: 'IMU', icon: Compass, message: 'Show me the IMU data' },
  { label: 'Status', icon: Zap, message: "What's the system status?" },
];

// Navigation action buttons for RobotTester mode
const NAV_ACTIONS = [
  { label: 'Forward', msg: 'Move forward 0.3 m' },
  { label: 'Backward', msg: 'Move backward 0.3 m' },
  { label: 'Left', msg: 'Strafe left 0.3 m' },
  { label: 'Right', msg: 'Strafe right 0.3 m' },
  { label: 'Spin L', msg: 'Spin left 90 degrees' },
  { label: 'Spin R', msg: 'Spin right 90 degrees' },
  { label: 'Stop', msg: 'Stop the robot immediately' },
  { label: 'Nav Status', msg: 'What is the navigation status?' },
  { label: 'Battery', msg: "What's the battery level?" },
];

export function ChatPanel({ className }: ChatPanelProps) {
  const {
    messages,
    isLoading,
    error,
    selectedProvider,
    mode,
    setSelectedProvider,
    setMode,
    sendMessage,
    resetChat,
    clearMessages,
  } = useChat();
  const [input, setInput] = useState('');
  const [providers, setProviders] = useState<string[]>([]);
  const [testReport, setTestReport] = useState<Record<string, unknown> | null>(null);
  const [testRunning, setTestRunning] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch available providers on mount
  useEffect(() => {
    fetch(`${CHAT_API_BASE}/api/providers`)
      .then(r => r.json())
      .then(d => setProviders(d.providers || []))
      .catch(() => setProviders([]));
  }, []);

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

  const handleNavAction = (msg: string) => {
    if (isLoading) return;
    sendMessage(msg, 'robot_tester');
  };

  const toggleTesterMode = () => {
    const newMode: ChatMode = mode === 'robot_tester' ? 'chat' : 'robot_tester';
    setMode(newMode);
    // Clear test report when switching modes
    setTestReport(null);
  };

  const runTestSuite = async () => {
    setTestRunning(true);
    setTestReport(null);
    try {
      const resp = await fetch(`${CHAT_API_BASE}/api/run_test_suite`, { method: 'POST' });
      const data = await resp.json();
      if (data.status === 'ok') {
        setTestReport(data.report);
      } else {
        setTestReport({ error: data.message || 'Test suite failed' });
      }
    } catch (e) {
      setTestReport({ error: String(e) });
    } finally {
      setTestRunning(false);
    }
  };

  const reviewWithAI = () => {
    if (!testReport) return;
    const reportText = JSON.stringify(testReport, null, 2);
    sendMessage(`Review this test report:\n\`\`\`json\n${reportText}\n\`\`\``, mode);
  };

  const isTesterMode = mode === 'robot_tester';

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header with provider selector and tester toggle */}
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-sm">OrbiBot AI</h3>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Provider selector */}
          <select
            value={selectedProvider ?? ''}
            onChange={e => setSelectedProvider(e.target.value || null)}
            disabled={isLoading}
            className="text-xs border rounded px-1.5 py-0.5 bg-background disabled:opacity-50"
            title="Select LLM provider"
          >
            <option value="">Default</option>
            {providers.map(p => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>

          {/* Tester mode toggle */}
          <button
            onClick={toggleTesterMode}
            disabled={isLoading}
            className={cn(
              'px-2 py-0.5 rounded text-xs font-medium transition-colors disabled:opacity-50',
              isTesterMode
                ? 'bg-amber-500 text-white'
                : 'border hover:bg-muted'
            )}
            title={isTesterMode ? 'Switch to Chat mode' : 'Switch to RobotTester mode'}
          >
            {isTesterMode ? 'Tester' : 'Chat'}
          </button>

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

      {/* Tester mode: Test suite runner */}
      {isTesterMode && (
        <div className="mb-3 p-2 border rounded-lg bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">Hardware Test Suite</span>
            <button
              onClick={runTestSuite}
              disabled={testRunning}
              className={cn(
                'flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors',
                'hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {testRunning ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Play className="w-3 h-3" />
              )}
              {testRunning ? 'Running...' : 'Run Tests'}
            </button>
          </div>

          {/* Test report display */}
          {testReport && !testReport.error && (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {Object.entries(testReport)
                .filter(([key]) => !key.startsWith('_'))
                .map(([name, result]: [string, any]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between text-xs border rounded px-2 py-1 bg-background"
                  >
                    <span className="capitalize">{name.replace(/_/g, ' ')}</span>
                    <div className="flex items-center gap-1">
                      {result.pass ? (
                        <CheckCircle2 className="w-3 h-3 text-green-500" />
                      ) : (
                        <XCircle className="w-3 h-3 text-red-500" />
                      )}
                      <span className={result.pass ? 'text-green-600' : 'text-red-600'}>
                        {result.pass ? 'PASS' : 'FAIL'}
                      </span>
                    </div>
                  </div>
                ))}
              {/* Summary */}
              {testReport._summary && (
                <div className="flex items-center justify-between text-xs pt-1 border-t mt-1">
                  <span className="text-muted-foreground">
                    {(testReport._summary as any).passed}/{(testReport._summary as any).total} passed
                  </span>
                  <button
                    onClick={reviewWithAI}
                    disabled={isLoading}
                    className="text-xs text-primary hover:underline disabled:opacity-50"
                  >
                    Review with AI
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Error display */}
          {testReport?.error && (
            <div className="text-xs text-red-500 p-2 bg-red-50 rounded">
              Error: {String(testReport.error)}
            </div>
          )}
        </div>
      )}

      {/* Navigation action buttons (tester mode only) */}
      {isTesterMode && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1.5">Quick nav actions</p>
          <div className="grid grid-cols-3 gap-1">
            {NAV_ACTIONS.map(action => (
              <button
                key={action.label}
                onClick={() => handleNavAction(action.msg)}
                disabled={isLoading}
                className={cn(
                  'text-xs border rounded px-1.5 py-1.5 transition-colors',
                  'hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quick actions — shown when conversation is empty and in chat mode */}
      {messages.length === 0 && !isTesterMode && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-2">Quick actions</p>
          <div className="grid grid-cols-2 gap-1.5">
            {QUICK_ACTIONS.map(action => (
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

      {/* Error display */}
      {error && (
        <div className="mb-2 p-2 text-xs text-red-500 bg-red-50 rounded border border-red-100">
          {error}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0 mb-2">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && !messages.some(m => m.role === 'assistant' && m.content === '' && m.liveTools) && (
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
          onChange={e => setInput(e.target.value)}
          placeholder={isTesterMode ? 'Enter test command...' : 'Ask OrbiBot...'}
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
        {/* Live tool progress while streaming */}
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
              '[&_li]:my-0.5 [&_code]:bg-muted/80 [&_code]:px-1 [&_code]:rounded [&_code]:font-mono [&_code]:text-xs',
              '[&_table]:text-xs [&_table]:border-collapse [&_th]:border [&_th]:px-2 [&_th]:py-1 [&_td]:border [&_td]:px-2 [&_td]:py-1'
            )}
          >
            {message.content ? (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            ) : message.liveTools ? (
              <span className="text-muted-foreground italic">Thinking...</span>
            ) : null}
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
