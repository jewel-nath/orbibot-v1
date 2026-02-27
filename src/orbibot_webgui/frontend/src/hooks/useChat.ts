/**
 * useChat — React hook for OrbiBot AI chat panel.
 *
 * Talks to the chat_server HTTP API (default port 8082).
 * Manages message history, loading state, and conversation reset.
 */

import { useState, useCallback, useRef } from 'react';

// Chat server lives on the same host, different port
const CHAT_API_BASE = `http://${window.location.hostname}:8082`;

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCallInfo[];
  timestamp: number;
}

export interface ToolCallInfo {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
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

  // Abort controller ref so we can cancel in-flight requests
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

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

    try {
      const resp = await fetch(`${CHAT_API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({}));
        throw new Error(errBody.error || `HTTP ${resp.status}`);
      }

      const data = await resp.json();

      const assistantMsg: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        content: data.reply || '',
        toolCalls: data.tool_calls?.length ? data.tool_calls : undefined,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);

      // Add error as assistant message so user sees it in chat
      const errMsg: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        content: `Error: ${message}`,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  }, []);

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

  return { messages, isLoading, error, sendMessage, resetChat, clearMessages };
}
