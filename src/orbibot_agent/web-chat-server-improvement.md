# Web Chat Server Improvement — Full Plan

This document explains **why** the chat server feels slower and less intelligent than MCP in Cursor,
and provides a **concrete, phased implementation plan** with exact files, APIs, and code patterns.

---

## 1. Root Cause Analysis

### 1.1 No Streaming — The Biggest Problem

**Current behaviour** in [`chat_server.py`](orbibot_agent/interfaces/chat_server.py) → `handle_chat()`:

```
User sends message
  → server runs process_message() (up to 10 tool rounds)
  → server returns ONE JSON blob when everything is done
  → user sees nothing for 5–30 seconds
```

**In Cursor + MCP:** you see the assistant "thinking", each tool call as it fires, and text chunks as they arrive.

**Effect:** Chat server feels much slower even when total wall-clock time is similar.

### 1.2 Weaker Default Model

**Current config** in [`agent_params.yaml`](config/agent_params.yaml):
```yaml
llm_providers:
  gemini:
    model: "gemini-3.1-flash-lite-preview"   # ← "lite" model
```

**In Cursor + MCP:** Cursor uses its own model (e.g. Claude Opus or Sonnet) for reasoning.
The MCP server only executes tools — the intelligence is Cursor's model.

**Effect:** Same tools, but the chat server uses a smaller model → less capable reasoning.

### 1.3 No Provider Choice in the UI

The frontend sends `{ message: trimmed }` only — no `provider` field.
The server already reads `body.get('provider')` but the UI never sends it.

**Effect:** Users cannot switch to Claude for harder tasks without editing config files.

### 1.4 Blocking Executor

`handle_chat()` calls `run_in_executor(None, ...)` which uses the
default shared thread pool. One long tool loop blocks a worker for the full duration.

**Effect:** No incremental feedback; possible request queuing under load.

### 1.5 No RobotTester Persona

The same generic system prompt is used for all requests.
There is no mode that forces methodical, step-by-step, pass/fail testing behaviour.

---

## 2. Implementation Plan — 8 Phases

---

### Phase 1 — SSE Streaming *(Highest Impact)*

**Goal:** User sees text chunks and tool progress as they happen, not after everything finishes.

#### 1a. New SSE endpoint in `chat_server.py`

Add `POST /api/chat/stream` alongside the existing `POST /api/chat`.

```python
# chat_server.py — new handler
async def handle_chat_stream(self, request: web.Request) -> web.StreamResponse:
    body = await request.json()
    message = body.get('message', '').strip()
    provider = body.get('provider', None)
    mode = body.get('mode', 'chat')          # 'chat' | 'robot_tester'

    resp = web.StreamResponse(headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    })
    await resp.prepare(request)

    async def send_event(data: dict):
        await resp.write(f"data: {json.dumps(data)}\n\n".encode())

    async with self._chat_lock:
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_stream():
            for event in self._agent.process_message_stream(message, mode=mode):
                loop.call_soon_threadsafe(queue.put_nowait, event)
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        loop.run_in_executor(self._chat_executor, run_stream)

        while True:
            event = await queue.get()
            if event is None:
                break
            await send_event(event)

    await resp.write_eof()
    return resp
```

**SSE event types:**

| Event | Payload | When |
|-------|---------|------|
| `text_chunk` | `{"event":"text_chunk","content":"..."}` | LLM emits a text token |
| `tool_start` | `{"event":"tool_start","name":"get_battery","args":{}}` | Before tool executes |
| `tool_result` | `{"event":"tool_result","name":"get_battery","result":{...}}` | After tool returns |
| `done` | `{"event":"done","tool_calls":[...]}` | All rounds complete |
| `error` | `{"event":"error","message":"..."}` | Any exception |

#### 1b. Add `process_message_stream()` to `agent_node.py`

```python
def process_message_stream(self, message: str, mode: str = 'chat'):
    """Generator that yields SSE event dicts as the agent works."""
    system_prompt = self._get_system_prompt(mode)
    # ... set provider, set prompt ...
    for chunk in self._current_provider.send_message_stream(message):
        if chunk.get('type') == 'text':
            yield {'event': 'text_chunk', 'content': chunk['content']}
        elif chunk.get('type') == 'tool_calls':
            for tc in chunk['tool_calls']:
                yield {'event': 'tool_start', 'name': tc['name'], 'args': tc['arguments']}
                result = self._tool_registry.execute_tool(tc['name'], tc['arguments'])
                yield {'event': 'tool_result', 'name': tc['name'], 'result': result}
            # send results back to LLM and continue streaming
            for next_chunk in self._current_provider.send_tool_results_stream(tool_results):
                yield next_chunk
    yield {'event': 'done', 'tool_calls': all_tool_calls}
```

#### 1c. Add `send_message_stream()` to `base_provider.py`

```python
@abstractmethod
def send_message_stream(self, message: str) -> Generator[Dict, None, None]:
    """Stream LLM response as chunks. Yields dicts with 'type': 'text' | 'tool_calls'."""
    pass
```

#### 1d. Implement streaming in each provider

| Provider | SDK method |
|----------|-----------|
| `gemini_provider.py` | `chat.send_message_stream(message)` → iterate `response` chunks |
| `anthropic_provider.py` | `client.messages.stream(...)` context manager → `text_stream` |
| `moonshot_provider.py` | OpenAI-compatible `stream=True` → iterate `chunk.choices[0].delta` |
| `ollama_provider.py` | OpenAI-compatible `stream=True` → iterate `chunk.choices[0].delta` |

#### 1e. Update `useChat.ts` — consume SSE

```typescript
// useChat.ts — new sendMessageStream()
const sendMessageStream = useCallback(async (text: string) => {
  // add user message immediately
  const resp = await fetch(`${CHAT_API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text, provider: selectedProvider, mode }),
  });

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let assistantContent = '';
  const liveToolCalls: ToolCallInfo[] = [];

  // add placeholder assistant message
  const assistantId = makeId();
  setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', timestamp: Date.now() }]);

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const line of decoder.decode(value).split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const event = JSON.parse(line.slice(6));
      if (event.event === 'text_chunk') {
        assistantContent += event.content;
        setMessages(prev => prev.map(m => m.id === assistantId
          ? { ...m, content: assistantContent } : m));
      } else if (event.event === 'tool_start') {
        // show live tool badge
        setMessages(prev => prev.map(m => m.id === assistantId
          ? { ...m, liveTools: [...(m.liveTools ?? []), event.name] } : m));
      } else if (event.event === 'tool_result') {
        liveToolCalls.push({ tool: event.name, args: {}, result: event.result });
      } else if (event.event === 'done') {
        setMessages(prev => prev.map(m => m.id === assistantId
          ? { ...m, toolCalls: liveToolCalls, liveTools: undefined } : m));
      }
    }
  }
}, [selectedProvider, mode]);
```

#### 1f. Update `ChatPanel.tsx` — show live tool badges

```tsx
{/* Live tool progress while streaming */}
{message.liveTools?.map(name => (
  <span key={name} className="inline-flex items-center gap-1 text-xs bg-muted rounded px-1.5 py-0.5 mr-1">
    <Loader2 className="w-2.5 h-2.5 animate-spin" />
    {name}
  </span>
))}
```

---

### Phase 2 — Stronger Default Model

**Goal:** Upgrade the default model so the chat server reasons as well as Cursor.

**Changes to [`agent_params.yaml`](config/agent_params.yaml):**

```yaml
llm_providers:
  gemini:
    model: "gemini-2.0-flash"            # upgraded from gemini-3.1-flash-lite-preview
    api_key_env: "GEMINI_API_KEY"

  anthropic:
    model: "claude-3-5-sonnet-20241022"
    api_key_env: "ANTHROPIC_API_KEY"

  moonshot:
    model: "kimi-latest"
    api_key_env: "MOONSHOT_API_KEY"

  ollama:
    model: "llama3.1:8b"
    base_url: "http://localhost:11434/v1"

# Per-mode model overrides (optional)
robot_tester:
  provider: "anthropic"                  # use Claude for tester mode
  model: "claude-3-5-sonnet-20241022"    # override model for tester

default_provider: "gemini"
```

**How it works in `agent_node.py`:**

```python
def _get_provider_for_mode(self, mode: str) -> str:
    if mode == 'robot_tester':
        return self._config.get('robot_tester', {}).get('provider', self._config.get('default_provider', 'gemini'))
    return self._config.get('default_provider', 'gemini')
```

---

### Phase 3 — Provider Selector in the UI

**Goal:** Let users switch to Claude or Gemini from the chat header without editing config.

#### 3a. `useChat.ts` — add `selectedProvider` state

```typescript
const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

// include in POST body:
body: JSON.stringify({ message: trimmed, provider: selectedProvider ?? undefined })
```

#### 3b. `ChatPanel.tsx` — provider dropdown in header

```tsx
// Fetch available providers on mount
const [providers, setProviders] = useState<string[]>([]);
useEffect(() => {
  fetch(`${CHAT_API_BASE}/api/providers`)
    .then(r => r.json())
    .then(d => setProviders(d.providers));
}, []);

// In the header:
<select
  value={selectedProvider ?? ''}
  onChange={e => setSelectedProvider(e.target.value || null)}
  className="text-xs border rounded px-1.5 py-0.5 bg-background"
>
  <option value="">Default</option>
  {providers.map(p => <option key={p} value={p}>{p}</option>)}
</select>
```

---

### Phase 4 — Dedicated Thread Pool

**Goal:** Prevent chat work from starving other async tasks; limit concurrency.

**Change in `chat_server.py` `__init__`:**

```python
from concurrent.futures import ThreadPoolExecutor

self._chat_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix='orbibot_chat'
)
```

**Then replace:**
```python
# Before:
result = await loop.run_in_executor(None, self._process_message_sync, message, provider)

# After:
result = await loop.run_in_executor(self._chat_executor, self._process_message_sync, message, provider)
```

---

### Phase 5 — RobotTester Mode

**Goal:** Same API and tools, but a methodical testing persona with pass/fail reporting.

#### 5a. New config file: `config/robot_tester_prompt.txt`

```
You are OrbiBot RobotTester — a systematic hardware and software test engineer.

BEHAVIOUR RULES:
1. Always state your test plan BEFORE calling any tools.
   Example: "Test plan: (1) get_encoder_counts baseline, (2) move_robot 0.5 m forward,
   (3) get_encoder_counts again, (4) compare delta vs expected."

2. After EACH tool call, report:
   - What was measured / what happened
   - PASS or FAIL with the reason
   - Expected vs actual values where applicable

3. For PID tuning:
   get_firmware_state → run_pid_test → interpret MAE and overshoot →
   suggest new Kp/Ki/Kd → set_motor_pid → run_pid_test again → summarize improvement.

4. For SLAM / Navigation:
   slam_get_map_info → set_initial_pose → navigate_to_pose → report status.
   Suggest next action: Forward / Backward / Left / Right / Stop.

5. For full hardware test:
   run_full_hardware_test → interpret each sub-result → list failures → suggest fixes.

6. End every test session with a SUMMARY TABLE:
   | Test | Result | Notes |
   |------|--------|-------|
   | ...  | PASS / FAIL | ... |

Always be concise. Use bullet points. Never skip the pass/fail verdict.
```

#### 5b. `agent_params.yaml` — add `robot_tester` section

```yaml
robot_tester:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
  prompt_file: "config/robot_tester_prompt.txt"
```

#### 5c. `agent_node.py` — load tester prompt and override provider

```python
def _get_system_prompt(self, mode: str = 'chat') -> str:
    if mode == 'robot_tester':
        prompt_file = self._config.get('robot_tester', {}).get('prompt_file', '')
        if prompt_file and os.path.exists(prompt_file):
            with open(prompt_file) as f:
                return f.read()
    return self._system_prompt  # default chat prompt

def process_message(self, message: str, mode: str = 'chat') -> Dict[str, Any]:
    provider_name = self._get_provider_for_mode(mode)
    if not self._current_provider or self._current_provider_name != provider_name:
        self.set_provider(provider_name)
    # override system prompt for this call
    self._current_provider.start_chat(self._get_system_prompt(mode))
    self._current_provider.set_tools(self._tool_registry.get_tool_schemas())
    # ... rest of loop unchanged ...
```

#### 5d. `chat_server.py` — read `mode` from request body

```python
async def handle_chat(self, request: web.Request) -> web.Response:
    body = await request.json()
    message = body.get('message', '').strip()
    provider = body.get('provider', None)
    mode = body.get('mode', 'chat')          # NEW

    async with self._chat_lock:
        result = await loop.run_in_executor(
            self._chat_executor,
            self._process_message_sync, message, provider, mode   # pass mode
        )
    return web.json_response(result)
```

#### 5e. `ChatPanel.tsx` — RobotTester toggle + nav action buttons

```tsx
const [testerMode, setTesterMode] = useState(false);

// In header:
<button
  onClick={() => setTesterMode(t => !t)}
  className={cn('px-2 py-1 rounded text-xs', testerMode ? 'bg-amber-500 text-white' : 'border')}
>
  Tester
</button>

// Nav action buttons (shown only in tester mode):
{testerMode && (
  <div className="grid grid-cols-3 gap-1 mb-2">
    {[
      { label: 'Forward', msg: 'Move forward 0.3 m' },
      { label: 'Backward', msg: 'Move backward 0.3 m' },
      { label: 'Left', msg: 'Strafe left 0.3 m' },
      { label: 'Right', msg: 'Strafe right 0.3 m' },
      { label: 'Spin L', msg: 'Spin left 90 degrees' },
      { label: 'Spin R', msg: 'Spin right 90 degrees' },
      { label: 'Stop', msg: 'Stop the robot immediately' },
      { label: 'Nav Status', msg: 'What is the navigation status?' },
      { label: 'Battery', msg: "What's the battery level?" },
    ].map(a => (
      <button key={a.label} onClick={() => sendMessage(a.msg, 'robot_tester')}
        className="text-xs border rounded px-1.5 py-1 hover:bg-muted">
        {a.label}
      </button>
    ))}
  </div>
)}
```

---

### Phase 6 — Structured Test Suite Endpoint

**Goal:** Reproducible, LLM-free test runs that return a JSON report; optional AI review.

#### 6a. New file: `orbibot_agent/core/test_suite_runner.py`

```python
class TestSuiteRunner:
    """Runs fixed hardware test sequences using the tool registry directly."""

    def __init__(self, tool_registry):
        self._tools = tool_registry

    def run_all(self) -> dict:
        return {
            'battery_test':  self._run_battery_test(),
            'encoder_test':  self._run_encoder_test(),
            'imu_test':      self._run_imu_test(),
            'motor_test':    self._run_motor_test(),
            'pid_test':      self._run_pid_test(),
        }

    def _run_battery_test(self) -> dict:
        result = self._tools.execute_tool('get_battery_status', {})
        voltage = result.get('voltage', 0)
        return {
            'pass': voltage > 10.5,
            'voltage': voltage,
            'details': result,
        }

    def _run_encoder_test(self) -> dict:
        before = self._tools.execute_tool('get_encoder_counts', {})
        self._tools.execute_tool('move_robot', {'linear_x': 0.2, 'duration': 1.0})
        after = self._tools.execute_tool('get_encoder_counts', {})
        delta = {k: after.get(k, 0) - before.get(k, 0) for k in before}
        return {
            'pass': all(abs(v) > 10 for v in delta.values()),
            'delta': delta,
            'details': {'before': before, 'after': after},
        }

    # ... _run_imu_test, _run_motor_test, _run_pid_test ...
```

#### 6b. `chat_server.py` — add `/api/run_test_suite` endpoint

```python
async def handle_run_test_suite(self, request: web.Request) -> web.Response:
    loop = asyncio.get_event_loop()
    try:
        report = await loop.run_in_executor(
            self._chat_executor,
            self._agent._tool_registry_runner.run_all
        )
        return web.json_response({'status': 'ok', 'report': report})
    except Exception as exc:
        return web.json_response({'status': 'error', 'message': str(exc)}, status=500)

# Register in build_app():
cors.add(app.router.add_post('/api/run_test_suite', self.handle_run_test_suite))
```

#### 6c. `ChatPanel.tsx` — test suite button + report display

```tsx
const [testReport, setTestReport] = useState<Record<string, unknown> | null>(null);
const [testRunning, setTestRunning] = useState(false);

const runTestSuite = async () => {
  setTestRunning(true);
  const resp = await fetch(`${CHAT_API_BASE}/api/run_test_suite`, { method: 'POST' });
  const data = await resp.json();
  setTestReport(data.report);
  setTestRunning(false);
};

// In tester mode panel:
<button onClick={runTestSuite} disabled={testRunning}
  className="w-full text-xs border rounded px-2 py-1.5 hover:bg-muted">
  {testRunning ? <Loader2 className="w-3 h-3 animate-spin inline mr-1" /> : null}
  Run Full Test Suite
</button>

{testReport && (
  <div className="mt-2 space-y-1">
    {Object.entries(testReport).map(([name, result]: [string, any]) => (
      <div key={name} className="flex items-center justify-between text-xs border rounded px-2 py-1">
        <span>{name.replace('_', ' ')}</span>
        <span className={result.pass ? 'text-green-500' : 'text-red-500'}>
          {result.pass ? 'PASS' : 'FAIL'}
        </span>
      </div>
    ))}
    <button
      onClick={() => sendMessage(`Review this test report:\n${JSON.stringify(testReport, null, 2)}`)}
      className="w-full text-xs border rounded px-2 py-1 hover:bg-muted mt-1"
    >
      Review with AI
    </button>
  </div>
)}
```

---

### Phase 7 — Client-Side Conversation History *(Optional)*

**Goal:** Resilience when the server session resets; useful for multi-instance deployments.

#### 7a. `useChat.ts` — send last 10 messages

```typescript
// In sendMessage / sendMessageStream:
const last10 = messages.slice(-10).map(m => ({ role: m.role, content: m.content }));
body: JSON.stringify({ message: trimmed, provider: selectedProvider, mode, messages: last10 })
```

#### 7b. `chat_server.py` — merge client history

```python
client_history = body.get('messages', [])  # [{role, content}, ...]
if client_history:
    self._agent._current_provider.inject_history(client_history)
```

Add `inject_history(messages)` to each provider to prepend the history before the new message.

---

### Phase 8 — README Update

Update [`README.md`](README.md) to document:

- New `POST /api/chat/stream` SSE endpoint and event types
- `mode=robot_tester` request parameter
- `POST /api/run_test_suite` endpoint and JSON report format
- Provider selector in the web UI
- `robot_tester` config section in `agent_params.yaml`

---

## 3. Architecture After All Phases

```
+---------------------------------------------------------------------+
|  ChatPanel.tsx                                                       |
|  +----------------+  +--------------+  +------------------------+  |
|  | Provider       |  | Tester       |  | Run Test Suite         |  |
|  | Selector       |  | Toggle       |  | + Report Display       |  |
|  +----------------+  +--------------+  +------------------------+  |
|  +----------------------------------------------------------------+  |
|  | Message list — live tool badges during streaming               |  |
|  |  [get_battery...]  [move_robot...]  → text chunks appear live  |  |
|  +----------------------------------------------------------------+  |
|  +----------------------------------------------------------------+  |
|  | Nav action buttons (tester mode only)                          |  |
|  |  Forward  Back  Left  Right  Spin L  Spin R  Stop             |  |
|  +----------------------------------------------------------------+  |
+---------------------------------------------------------------------+
                | useChat.ts (SSE reader + provider + mode)
                v
+---------------------------------------------------------------------+
|  chat_server.py  (port 8082)                                        |
|  POST /api/chat          → blocking JSON (kept for compatibility)   |
|  POST /api/chat/stream   → SSE stream (new)                         |
|  POST /api/run_test_suite → JSON report (new)                       |
|  GET  /api/providers     → list available providers                 |
|  GET  /api/health        → health check                             |
|  POST /api/reset         → reset chat session                       |
+---------------------------------------------------------------------+
                | ThreadPoolExecutor(max_workers=2)
                v
+---------------------------------------------------------------------+
|  agent_node.py                                                      |
|  process_message(msg, mode)         → blocking (existing)           |
|  process_message_stream(msg, mode)  → generator yielding SSE events |
|  _get_system_prompt(mode)           → chat or robot_tester prompt   |
|  _get_provider_for_mode(mode)       → default or robot_tester prov  |
+---------------------------------------------------------------------+
                |
        +-------+--------+
        v                v
+--------------+  +----------------------------------------------+
| LLM Providers|  | core/test_suite_runner.py                    |
| gemini       |  | run_all() → {battery, encoder, imu, motor}   |
| anthropic    |  | Each test: pass/fail + details dict           |
| moonshot     |  +----------------------------------------------+
| ollama       |
| (all stream) |
+--------------+
```

---

## 4. Summary Table

| Phase | What Changes | Files | Impact |
|-------|-------------|-------|--------|
| 1 — SSE Streaming | New `/api/chat/stream` endpoint; streaming in all providers; live UI | `chat_server.py`, `agent_node.py`, all 4 providers, `useChat.ts`, `ChatPanel.tsx` | Highest — eliminates perceived slowness |
| 2 — Stronger Model | Upgrade default model; per-mode model overrides | `agent_params.yaml` | High — immediate intelligence boost |
| 3 — Provider Selector | Provider dropdown in chat header | `useChat.ts`, `ChatPanel.tsx` | Medium — user control |
| 4 — Thread Pool | Dedicated executor for chat | `chat_server.py` | Low — concurrency improvement |
| 5 — RobotTester Mode | Tester persona, prompt, nav buttons | `chat_server.py`, `agent_node.py`, new prompt file, `agent_params.yaml`, `ChatPanel.tsx` | High — new capability |
| 6 — Test Suite | LLM-free test runs + AI review | new `test_suite_runner.py`, `chat_server.py`, `ChatPanel.tsx` | Medium — reproducible testing |
| 7 — Client History | Frontend sends last 10 messages | `useChat.ts`, `chat_server.py` | Low — resilience |
| 8 — README | Document all new features | `README.md` | Documentation |

---

## 5. File Change Summary

| File | Change |
|------|--------|
| [`orbibot_agent/interfaces/chat_server.py`](orbibot_agent/interfaces/chat_server.py) | Add `handle_chat_stream`, `handle_run_test_suite`; read `mode`; add `ThreadPoolExecutor` |
| [`orbibot_agent/agent_node.py`](orbibot_agent/agent_node.py) | Add `process_message_stream`, `_get_system_prompt(mode)`, `_get_provider_for_mode(mode)` |
| [`orbibot_agent/llm_providers/base_provider.py`](orbibot_agent/llm_providers/base_provider.py) | Add abstract `send_message_stream()` and `inject_history()` |
| [`orbibot_agent/llm_providers/gemini_provider.py`](orbibot_agent/llm_providers/gemini_provider.py) | Implement `send_message_stream()` |
| [`orbibot_agent/llm_providers/anthropic_provider.py`](orbibot_agent/llm_providers/anthropic_provider.py) | Implement `send_message_stream()` |
| [`orbibot_agent/llm_providers/moonshot_provider.py`](orbibot_agent/llm_providers/moonshot_provider.py) | Implement `send_message_stream()` |
| [`orbibot_agent/llm_providers/ollama_provider.py`](orbibot_agent/llm_providers/ollama_provider.py) | Implement `send_message_stream()` |
| [`orbibot_agent/core/test_suite_runner.py`](orbibot_agent/core/test_suite_runner.py) | **New file** — `TestSuiteRunner` class |
| [`config/agent_params.yaml`](config/agent_params.yaml) | Upgrade model; add `robot_tester` section |
| [`config/robot_tester_prompt.txt`](config/robot_tester_prompt.txt) | **New file** — RobotTester system prompt |
| [`orbibot_webgui/frontend/src/hooks/useChat.ts`](../orbibot_webgui/frontend/src/hooks/useChat.ts) | Add `sendMessageStream`, `selectedProvider`, `mode`, client history |
| [`orbibot_webgui/frontend/src/components/navigation/ChatPanel.tsx`](../orbibot_webgui/frontend/src/components/navigation/ChatPanel.tsx) | Add provider selector, tester toggle, nav buttons, test suite UI, live tool badges |
| [`README.md`](README.md) | Document all new endpoints and features |
