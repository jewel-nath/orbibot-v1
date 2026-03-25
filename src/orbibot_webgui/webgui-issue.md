# OrbiBot Web GUI — Known Issues & Technical Debt

---

## Active Issues

### [BUG] Settings WebSocket URL may not take effect on reconnect
**File:** `frontend/src/contexts/RosContext.tsx`
**Severity:** Low
**Description:**
If the WebSocket URL is changed in Settings while a reconnect cycle is already in progress,
the new URL might not be used until the current cycle completes. The `reconnect()` function
reads `wsUrl` state at call time; a URL change during the backoff window is picked up only
on the next manual reconnect or page reload.
**Workaround:** Reload the page after changing the WebSocket URL.

---

### [BUG] Speed change mid-keystroke sends stale velocity
**File:** `frontend/src/features/control/MecanumController.tsx`
**Severity:** Low
**Description:**
Adjusting the speed slider while holding a movement key leaves the active publishing
interval sending the velocity computed before the speed change. The keyboard handler
effect re-runs (clearing pressed keys) but does not restart the interval.
**Impact:** Robot runs at the old speed for up to ~100 ms after a speed change.
**Fix:** Track `speedPercent` in a ref and recompute velocity inside the interval callback.

---

### [BUG] WebRTC stream not cleared after disconnect
**File:** `frontend/src/hooks/useWebRTC.ts`
**Severity:** Low
**Description:**
When a WebRTC connection fails after a track has been received, the `stream` state is not
reset to `null`. `CameraFeed` may show a frozen frame instead of the offline placeholder
until a successful reconnect replaces the stream.
**Fix:** Call `setStream(null)` in all connection failure paths.

---

### [BUG] AbortSignal.timeout() may fail in older browsers
**File:** `frontend/src/hooks/useChat.ts`
**Severity:** Low
**Description:**
`AbortSignal.timeout(3000)` is not available in browsers released before mid-2022
(Chrome < 103, Firefox < 100, Safari < 16). `checkConnection` will throw a `TypeError`
in those environments.
**Fix:** Replace with `AbortController` + `setTimeout` fallback or a feature check.

---

## Technical Debt

### [DEBT] No unit or integration tests
The frontend has zero automated test coverage. Critical paths — ROS connection, velocity
publishing, navigation goal placement, PID tuning — are untested.
**Priority:** Medium
**Suggested tools:** Vitest + React Testing Library; Playwright for E2E.

---

### [DEBT] SettingsContext lacks input validation
**File:** `frontend/src/contexts/SettingsContext.tsx`
**Description:**
Settings from `localStorage` are spread directly onto `DEFAULT_SETTINGS` with no schema
validation. A malformed stored value (e.g. a corrupted URL) silently persists and causes
confusing failures.
**Fix:** Validate parsed settings with Zod or a manual shape check before applying.

---

### [DEBT] Frontend build not triggered by colcon build
**File:** `setup.py`
**Description:**
`setup.py` only includes `frontend/dist` if the directory already exists at build time.
On a fresh clone, `colcon build` succeeds but the installed package has no frontend assets.
**Fix:** Invoke `npm ci && npm run build` from `setup.py` or a colcon pre-build hook.

---

### [DEBT] useWebRTC hook is too large (~460 lines)
**File:** `frontend/src/hooks/useWebRTC.ts`
**Description:**
Peer-connection setup, ICE gathering, track handling, and reconnect backoff are all inside
one function, making individual concerns difficult to test or replace.
**Suggested split:**
- `lib/webrtc/createPeerConnection.ts`
- `lib/webrtc/waitForICEGathering.ts`
- `useWebRTCReconnect.ts` for reconnect state only

---

### [DEBT] No mobile PWA manifest
The `/controller` route works on phone/tablet but the app lacks a PWA manifest and
optimised viewport meta tags. The full dashboard is not responsive below ~768 px.

---

## Resolved Issues

| Issue | Fixed in |
|-------|---------|
| Navigation goal placed at wrong position on rotated map | v2.1.0 |
| Chat API URL hardcoded — not configurable | Unreleased |
| `quaternionToEuler` duplicated in `useIMU` and `useOdometry` | Unreleased |
| Magic nav goal status codes (1, 2, 4, 5, 6) | Unreleased |
| G15 internal review markers left in `RosContext` | Unreleased |
