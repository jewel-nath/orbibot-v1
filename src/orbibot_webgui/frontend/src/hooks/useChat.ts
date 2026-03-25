/**
 * useChat — React hook for OrbiBot AI chat panel.
 *
 * Talks to the chat_server HTTP API (default port 8082).
 * Supports SSE streaming, provider selection, RobotTester mode,
 * client-side conversation history, and fallback to blocking requests.
 */

import { useState, useCallback, useRef } from 'react';

const CHAT_API_BASE = `http://${window.location.hostname}:8082`;

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCallInfo[];
  /** Tool names currently executing (streaming only) */
  liveTools?: string[];
  timestamp: number;
}

export interface ToolCallInfo {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

export type ChatMode = 'chat' | 'robot_tester';

export interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  connected: boolean;
  selectedProvider: string | null;
  mode: ChatMode;
  setSelectedProvider: (p: string | null) => void;
  setMode: (m: ChatMode) => void;
  sendMessage: (text: string, modeOverride?: ChatMode) => Promise<void>;
  resetChat: () => Promise<void>;
  clearMessages: () => void;
  checkConnection: () => Promise<boolean>;
}

let _nextId = 0;
function makeId(): string {
  _nextId += 1;
  return `msg-${Date.now()}-${_nextId}`;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>('chat');

  const abortRef = useRef<AbortController | null>(null);
  // Keep a ref to messages so streaming helpers can read current state
  // without needing setState-as-getter hack
  const messagesRef = useRef<ChatMessage[]>([]);
  messagesRef.current = messages;

  const checkConnection = useCallback(async (): Promise<boolean> => {
    try {
      const resp = await fetch(`${CHAT_API_BASE}/api/health`, {
        signal: AbortSignal.timeout(3000),
      });
      const ok = resp.ok;
      setConnected(ok);
      return ok;
    } catch {
      setConnected(false);
      return false;
    }
  }, []);

  const sendMessage = useCallback(async (text: string, modeOverride?: ChatMode) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const activeMode = modeOverride ?? mode;

    // Add user message immediately
    const userMsg: ChatMessage = {
      id: makeId(),
      role: 'user',
      content: trimmed,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Build last-10 history for context recovery
    const history = messagesRef.current
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }));

    // Try SSE streaming first, fall back to blocking
    try {
      await sendMessageStream(
        trimmed, activeMode, selectedProvider, controller, setMessages, history,
      );
      setConnected(true);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setIsLoading(false);
        return;
      }

      try {
        await sendMessageBlocking(
          trimmed, activeMode, selectedProvider, controller, setMessages, history,
        );
        setConnected(true);
      } catch (fallbackErr: unknown) {
        if (fallbackErr instanceof DOMException && fallbackErr.name === 'AbortError') {
          setIsLoading(false);
          return;
        }
        const message = fallbackErr instanceof Error ? fallbackErr.message : 'Connection failed';
        setError(message);
        setConnected(false);
        setMessages(prev => [...prev, {
          id: makeId(),
          role: 'assistant',
          content: `Error: ${message}`,
          timestamp: Date.now(),
        }]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [mode, selectedProvider]);

  const resetChat = useCallback(async () => {
    try {
      await fetch(`${CHAT_API_BASE}/api/reset`, { method: 'POST' });
    } catch {
      // Best-effort
    }
    setMessages([]);
    setError(null);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages, isLoading, error, connected,
    selectedProvider, mode,
    setSelectedProvider, setMode,
    sendMessage, resetChat, clearMessages, checkConnection,
  };
}

// ---------------------------------------------------------------------------
// SSE streaming
// ---------------------------------------------------------------------------

async function sendMessageStream(
  message: string,
  mode: ChatMode,
  provider: string | null,
  controller: AbortController,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  history: Array<{ role: string; content: string }>,
): Promise<void> {
  const resp = await fetch(`${CHAT_API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      provider: provider ?? undefined,
      mode,
      messages: history,
    }),
    signal: controller.signal,
  });

  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  if (!resp.body) throw new Error('No response body for SSE stream');

  const assistantId = makeId();
  setMessages(prev => [
    ...prev,
    { id: assistantId, role: 'assistant', content: '', liveTools: [], timestamp: Date.now() },
  ]);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let assistantContent = '';
  const toolCalls: ToolCallInfo[] = [];
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;

      let event: Record<string, unknown>;
      try {
        event = JSON.parse(raw);
      } catch {
        continue;
      }

      switch (event.event) {
        case 'text_chunk':
          assistantContent += (event.content as string) ?? '';
          setMessages(prev =>
            prev.map(m => m.id === assistantId ? { ...m, content: assistantContent } : m)
          );
          break;

        case 'tool_start':
          setMessages(prev =>
            prev.map(m => m.id === assistantId
              ? { ...m, liveTools: [...(m.liveTools ?? []), event.name as string] }
              : m)
          );
          break;

        case 'tool_result':
          toolCalls.push({
            tool: event.name as string,
            args: (event.args as Record<string, unknown>) ?? {},
            result: (event.result as Record<string, unknown>) ?? {},
          });
          // Remove from live tools
          setMessages(prev =>
            prev.map(m => m.id === assistantId
              ? { ...m, liveTools: (m.liveTools ?? []).filter(t => t !== event.name) }
              : m)
          );
          break;

        case 'done':
          setMessages(prev =>
            prev.map(m => m.id === assistantId
              ? { ...m, toolCalls: toolCalls.length ? toolCalls : undefined, liveTools: undefined }
              : m)
          );
          break;

        case 'error':
          setMessages(prev =>
            prev.map(m => m.id === assistantId
              ? { ...m, content: `Error: ${event.message}`, liveTools: undefined }
              : m)
          );
          break;
      }
    }
  }

  // Ensure liveTools is cleared even if 'done' event was missed
  setMessages(prev =>
    prev.map(m => m.id === assistantId && m.liveTools !== undefined
      ? { ...m, liveTools: undefined }
      : m)
  );
}

// ---------------------------------------------------------------------------
// Blocking fallback
// ---------------------------------------------------------------------------

async function sendMessageBlocking(
  message: string,
  mode: ChatMode,
  provider: string | null,
  controller: AbortController,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  history: Array<{ role: string; content: string }>,
): Promise<void> {
  const resp = await fetch(`${CHAT_API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      provider: provider ?? undefined,
      mode,
      messages: history,
    }),
    signal: controller.signal,
  });

  if (!resp.ok) {
    const errBody = await resp.json().catch(() => ({}));
    throw new Error((errBody as { error?: string }).error || `HTTP ${resp.status}`);
  }

  const data = await resp.json() as { reply?: string; tool_calls?: ToolCallInfo[] };
  setMessages(prev => [...prev, {
    id: makeId(),
    role: 'assistant',
    content: data.reply || '',
    toolCalls: data.tool_calls?.length ? data.tool_calls : undefined,
    timestamp: Date.now(),
  }]);
}
