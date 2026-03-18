/**
 * useChat — React hook for OrbiBot AI chat panel.
 *
 * Talks to the chat_server HTTP API (default port 8082).
 * Supports:
 *   - SSE streaming via POST /api/chat/stream (Phase 1)
 *   - Provider selection (Phase 3)
 *   - RobotTester mode (Phase 5)
 *   - Client-side conversation history (Phase 7)
 *   - Fallback to blocking POST /api/chat
 */

import { useState, useCallback, useRef, Dispatch, SetStateAction } from 'react';

// Chat server lives on the same host, different port
const CHAT_API_BASE = `http://${window.location.hostname}:8082`;

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCallInfo[];
  /** Live tool names currently executing (streaming only) */
  liveTools?: string[];
  timestamp: number;
}

export interface ToolCallInfo {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

export type ChatMode = 'chat' | 'robot_tester';

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  selectedProvider: string | null;
  mode: ChatMode;
  setSelectedProvider: (p: string | null) => void;
  setMode: (m: ChatMode) => void;
  sendMessage: (text: string, modeOverride?: ChatMode) => Promise<void>;
  resetChat: () => Promise<void>;
  clearMessages: () => void;
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
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>('chat');

  // Abort controller ref so we can cancel in-flight requests
  const abortRef = useRef<AbortController | null>(null);

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

    // Cancel any previous in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Build last-10 history for context recovery (Phase 7)
    // We read messages from state snapshot before adding userMsg
    // (userMsg is added above but we capture the snapshot here)
    const buildHistory = (msgs: ChatMessage[]) =>
      msgs.slice(-10).map(m => ({ role: m.role, content: m.content }));

    // Try SSE streaming first (Phase 1)
    try {
      await sendMessageStream(
        trimmed,
        activeMode,
        selectedProvider,
        controller,
        setMessages,
        buildHistory,
      );
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setIsLoading(false);
        return;
      }

      // SSE failed — fall back to blocking request
      try {
        await sendMessageBlocking(
          trimmed,
          activeMode,
          selectedProvider,
          controller,
          setMessages,
          buildHistory,
        );
      } catch (fallbackErr: unknown) {
        if (fallbackErr instanceof DOMException && fallbackErr.name === 'AbortError') {
          setIsLoading(false);
          return;
        }
        const message = fallbackErr instanceof Error ? fallbackErr.message : 'Unknown error';
        setError(message);
        const errMsg: ChatMessage = {
          id: makeId(),
          role: 'assistant',
          content: `Error: ${message}`,
          timestamp: Date.now(),
        };
        setMessages(prev => [...prev, errMsg]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [mode, selectedProvider]);

  const resetChat = useCallback(async () => {
    try {
      await fetch(`${CHAT_API_BASE}/api/reset`, { method: 'POST' });
    } catch {
      // Best-effort reset
    }
    setMessages([]);
    setError(null);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
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
  };
}

// ---------------------------------------------------------------------------
// SSE streaming implementation (Phase 1)
// ---------------------------------------------------------------------------

async function sendMessageStream(
  message: string,
  mode: ChatMode,
  provider: string | null,
  controller: AbortController,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  buildHistory: (msgs: ChatMessage[]) => Array<{ role: string; content: string }>,
): Promise<void> {
  // Capture current messages for history (before the new user message was added)
  // We use a ref-like approach: read from the DOM state via a functional update
  let capturedHistory: Array<{ role: string; content: string }> = [];
  setMessages(prev => {
    capturedHistory = buildHistory(prev.slice(0, -1)); // exclude the just-added user msg
    return prev;
  });

  const resp = await fetch(`${CHAT_API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      provider: provider ?? undefined,
      mode,
      messages: capturedHistory,
    }),
    signal: controller.signal,
  });

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }

  if (!resp.body) {
    throw new Error('No response body for SSE stream');
  }

  // Add placeholder assistant message
  const assistantId = makeId();
  setMessages(prev => [
    ...prev,
    { id: assistantId, role: 'assistant', content: '', liveTools: [], timestamp: Date.now() },
  ]);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let assistantContent = '';
  const liveToolCalls: ToolCallInfo[] = [];
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? ''; // keep incomplete line in buffer

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

      if (event.event === 'text_chunk') {
        assistantContent += (event.content as string) ?? '';
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId ? { ...m, content: assistantContent } : m
          )
        );
      } else if (event.event === 'tool_start') {
        const toolName = event.name as string;
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, liveTools: [...(m.liveTools ?? []), toolName] }
              : m
          )
        );
      } else if (event.event === 'tool_result') {
        liveToolCalls.push({
          tool: event.name as string,
          args: (event.args as Record<string, unknown>) ?? {},
          result: (event.result as Record<string, unknown>) ?? {},
        });
      } else if (event.event === 'done') {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, toolCalls: liveToolCalls.length ? liveToolCalls : undefined, liveTools: undefined }
              : m
          )
        );
      } else if (event.event === 'error') {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: `Error: ${event.message}`, liveTools: undefined }
              : m
          )
        );
      }
    }
  }

  // Ensure liveTools is cleared even if 'done' event was missed
  setMessages(prev =>
    prev.map(m =>
      m.id === assistantId && m.liveTools !== undefined
        ? { ...m, liveTools: undefined }
        : m
    )
  );
}

// ---------------------------------------------------------------------------
// Blocking fallback (Phase 1 fallback / backward-compat)
// ---------------------------------------------------------------------------

async function sendMessageBlocking(
  message: string,
  mode: ChatMode,
  provider: string | null,
  controller: AbortController,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  buildHistory: (msgs: ChatMessage[]) => Array<{ role: string; content: string }>,
): Promise<void> {
  let capturedHistory: Array<{ role: string; content: string }> = [];
  setMessages(prev => {
    capturedHistory = buildHistory(prev.slice(0, -1));
    return prev;
  });

  const resp = await fetch(`${CHAT_API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      provider: provider ?? undefined,
      mode,
      messages: capturedHistory,
    }),
    signal: controller.signal,
  });

  if (!resp.ok) {
    const errBody = await resp.json().catch(() => ({}));
    throw new Error((errBody as { error?: string }).error || `HTTP ${resp.status}`);
  }

  const data = await resp.json() as { reply?: string; tool_calls?: unknown[] };

  const assistantMsg: ChatMessage = {
    id: makeId(),
    role: 'assistant',
    content: data.reply || '',
    toolCalls: data.tool_calls?.length
      ? (data.tool_calls as ToolCallInfo[])
      : undefined,
    timestamp: Date.now(),
  };
  setMessages(prev => [...prev, assistantMsg]);
}
