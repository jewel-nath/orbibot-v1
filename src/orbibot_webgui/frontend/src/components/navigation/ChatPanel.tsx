/**
 * ChatPanel — AI chat interface for OrbiBot.
 *
 * Lives inside MissionControl tabs. Sends natural language to
 * the chat_server HTTP API and displays streaming responses.
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
  CheckCircle2,
  XCircle,
  WifiOff,
  RefreshCw,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useChat } from '@/hooks/useChat';
import type { ChatMessage, ToolCallInfo } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  className?: string;
}

const CHAT_API_BASE = `http://${window.location.hostname}:8082`;

const QUICK_ACTIONS = [
  { label: 'Battery?', icon: Battery, message: "What's the battery level?" },
  { label: 'Where?', icon: MapPin, message: 'Where are you right now?' },
  { label: 'IMU', icon: Compass, message: 'Show me the IMU data' },
  { label: 'Status', icon: Zap, message: "What's the system status?" },
];

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

interface TestSummary {
  total: number;
  passed: number;
  failed: number;
  all_pass: boolean;
}

interface TestResult {
  pass?: boolean;
  verdict?: string;
  [key: string]: unknown;
}

interface TestReport {
  _summary?: TestSummary;
  _error?: string;
  [key: string]: TestResult | TestSummary | string | undefined;
}

export function ChatPanel({ className }: ChatPanelProps) {
  const {
    messages, isLoading, error, connected,
    selectedProvider, mode,
    setSelectedProvider, setMode,
    sendMessage, resetChat, checkConnection,
  } = useChat();
  const [input, setInput] = useState('');
  const [providers, setProviders] = useState<string[]>([]);
  const [testReport, setTestReport] = useState<TestReport | null>(null);
  const [testRunning, setTestRunning] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch providers and check connection on mount
  useEffect(() => {
    fetch(`${CHAT_API_BASE}/api/providers`)
      .then(r => r.json())
      .then(d => setProviders(d.providers || []))
      .catch(() => setProviders([]));
    checkConnection();
  }, [checkConnection]);

  // Auto-scroll on new messages
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
    setMode(mode === 'robot_tester' ? 'chat' : 'robot_tester');
    setTestReport(null);
  };

  const runTestSuite = async () => {
    setTestRunning(true);
    setTestReport(null);
    try {
      const resp = await fetch(`${CHAT_API_BASE}/api/run_test_suite`, { method: 'POST' });
      const data = await resp.json();
      setTestReport(data.status === 'ok' ? data.report : { _error: data.message || 'Test suite failed' });
    } catch (e) {
      setTestReport({ _error: String(e) });
    } finally {
      setTestRunning(false);
    }
  };

  const reviewWithAI = () => {
    if (!testReport) return;
    sendMessage(
      `Review this test report:\n\`\`\`json\n${JSON.stringify(testReport, null, 2)}\n\`\`\``,
      mode,
    );
  };

  const isTesterMode = mode === 'robot_tester';
  const hasStreamingMessage = messages.some(m => m.role === 'assistant' && m.liveTools !== undefined);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
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

          {/* Mode toggle */}
          <button
            onClick={toggleTesterMode}
            disabled={isLoading}
            className={cn(
              'px-2 py-0.5 rounded text-xs font-medium transition-colors disabled:opacity-50',
              isTesterMode ? 'bg-amber-500 text-white' : 'border hover:bg-muted',
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

      {/* Tester: Test suite runner */}
      {isTesterMode && (
        <div className="mb-3 p-2 border rounded-lg bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">Hardware Test Suite</span>
            <button
              onClick={runTestSuite}
              disabled={testRunning}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors hover:bg-muted disabled:opacity-50"
            >
              {testRunning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              {testRunning ? 'Running...' : 'Run Tests'}
            </button>
          </div>

          {testReport && !testReport._error && (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {Object.entries(testReport)
                .filter(([key]) => !key.startsWith('_'))
                .map(([name, rawResult]) => {
                  const result = rawResult as TestResult;
                  return (
                    <div key={name} className="flex items-center justify-between text-xs border rounded px-2 py-1 bg-background">
                      <span className="capitalize">{name.replace(/_/g, ' ')}</span>
                      <div className="flex items-center gap-1">
                        {result.pass
                          ? <CheckCircle2 className="w-3 h-3 text-green-500" />
                          : <XCircle className="w-3 h-3 text-red-500" />}
                        <span className={result.pass ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                          {result.pass ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              {testReport._summary && (
                <div className="flex items-center justify-between text-xs pt-1 border-t mt-1">
                  <span className="text-muted-foreground">
                    {testReport._summary.passed}/{testReport._summary.total} passed
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

          {testReport?._error && (
            <div className="text-xs text-destructive p-2 bg-destructive/10 rounded">
              Error: {String(testReport._error)}
            </div>
          )}
        </div>
      )}

      {/* Tester: Nav action buttons */}
      {isTesterMode && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1.5">Quick nav actions</p>
          <div className="grid grid-cols-3 gap-1">
            {NAV_ACTIONS.map(action => (
              <button
                key={action.label}
                onClick={() => handleNavAction(action.msg)}
                disabled={isLoading}
                className="text-xs border rounded px-1.5 py-1.5 transition-colors hover:bg-muted disabled:opacity-50"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quick actions — shown when empty in chat mode */}
      {messages.length === 0 && !isTesterMode && (
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-2">Quick actions</p>
          <div className="grid grid-cols-2 gap-1.5">
            {QUICK_ACTIONS.map(action => (
              <button
                key={action.label}
                onClick={() => handleQuickAction(action.message)}
                disabled={isLoading || !connected}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs border hover:bg-muted/50 transition-colors disabled:opacity-50"
              >
                <action.icon className="w-3 h-3 text-primary" />
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mb-2 p-2 text-xs text-destructive bg-destructive/10 rounded border border-destructive/20 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => checkConnection()} className="ml-2 hover:underline flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0 mb-2">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && !hasStreamingMessage && (
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
          placeholder={
            !connected ? 'Chat server offline...'
            : isTesterMode ? 'Enter test command...'
            : 'Ask OrbiBot...'
          }
          disabled={isLoading || !connected}
          className={cn(
            'flex-1 px-3 py-2 rounded-lg text-sm',
            'bg-muted/50 border focus:outline-none focus:ring-1 focus:ring-primary',
            'disabled:opacity-50 placeholder:text-muted-foreground/60',
          )}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim() || !connected}
          className="p-2 rounded-lg transition-colors bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
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

        {/* Completed tool calls (collapsible) */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallsSummary calls={message.toolCalls} />
        )}

        {/* Message content */}
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
