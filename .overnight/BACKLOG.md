# Overnight Auto-Research Backlog

Shared file between the BA/PM persona (adds to Proposed) and the Engineer
persona (moves Proposed -> Shipped or Abandoned). Newest proposals go at
the TOP of their section. Read `.overnight/GUARDRAILS.md` before touching
this file or the codebase.

## Proposed

*(PM cycle 2026-07-10 ~03:20 IST added the 3 items below to the top —
grounded in a fresh re-read of linux/src/dashphone/ against the current
BACKLOG/state after the bind_failed ship, see state.md for the
rationale on each)*

1. **Detect and notify on a missed call (RINGING → CALL_ENDED with no
   CALL_ACTIVE in between).** `state/call_state_controller.py`'s
   `handle_event` currently treats every `CALL_ENDED` the same way —
   it just calls `self._set_state(CallState.idle())`, with no
   distinction between "call was answered and then hung up" and "call
   rang out / was declined on the phone itself while this app's popup
   was showing". Since `self._state.phase` still holds the *previous*
   phase at the top of the `CALL_ENDED` branch (before
   `_set_state` overwrites it), a one-line check
   (`self._state.phase is CallPhase.RINGING`) is enough to tell the two
   apart. Add a new `call_missed = Signal(str, str)` (name, number) on
   `CallStateController`, emitted right before the idle transition when
   that condition holds; wire it in `app.py`
   (`controller.call_missed.connect(...)`) to a new small
   `TrayIcon.notify_missed_call(name, number)` that fires
   `showMessage()` (same pattern already proven working under
   `QT_QPA_PLATFORM=offscreen` by the shipped `bind_failed` feature).
   Purely additive, no protocol change (still just reacting to the
   existing `CALL_ENDED` message). Testable entirely in
   `linux/tests/test_call_state.py` with no Qt/GUI needed: assert the
   signal fires with the right name/number for
   `CALL_RINGING → CALL_ENDED`, and does *not* fire for
   `CALL_RINGING → CALL_ACTIVE → CALL_ENDED` (a normal completed call).
   Distinct from Proposed item 10 below (`CallState` history/last-call
   summary) — this is a single real-time notification of one specific
   event type, not a persistent list; the two could complement each
   other later but neither depends on the other.
2. **"Decline" action in the tray dropdown while ringing, not just in
   the popup.** `ui/tray_icon.py` only ever shows `_hangup_action`
   (visible when `state.phase is CallPhase.ACTIVE`) — there is no way
   to decline an incoming call from the tray if the popup
   (`ui/call_popup.py`) is obscured, on another workspace, or the
   compositor fails to raise it, which is exactly the failure mode
   Proposed item 4 below (desktop notification) is trying to make more
   *visible*, but that item alone still forces the user to go find the
   popup to act on it. Add a `_decline_action` beside `_hangup_action`,
   following the exact same `setVisible(is_ringing)` pattern already
   used for `_timer_action`/`_hangup_action`'s `is_active` toggle in
   `_refresh()`, wired to a new `on_decline: Callable[[], None]`
   constructor parameter (mirrors the existing `on_hangup` param
   exactly). In `app.py`, pass
   `on_decline=lambda: controller.send_command(MessageType.REJECT)` —
   the same command the popup's Decline button already sends, so no
   protocol/state-machine change at all. Testable the same way
   `test_tray_icon.py` already tests `_hangup_action`'s visibility and
   `on_hangup` invocation: assert `_decline_action` is hidden when
   idle/active, visible when `set_state(CallState.ringing(...))`, and
   that triggering it calls the injected callback.
3. **Surface `HfpManager.status_changed` in the tray instead of only
   logging it.** Confirmed via grep across `linux/src/dashphone/` that
   `HfpManager.status_changed` (defined + emitted in
   `bluetooth/hfp_manager.py` — "No paired phone found", "Found paired
   phone: X", "Speaking through X", "Phone did not appear as an audio
   device - check Android's Bluetooth 'Phone calls' toggle...") has
   zero `.connect(` targets anywhere, same shape of silent-gap as the
   already-shipped `bind_failed` wiring (see Shipped section) but for
   Bluetooth call-audio status instead of the WebSocket port. Right now
   the *only* way to know whether Bluetooth HFP routing found a phone,
   is retrying, gave up, or succeeded is to read the log file by hand —
   directly relevant to the "Known blocker" troubleshooting section
   already documented in `linux/README.md`'s Bluetooth call audio
   section. Add a small `TrayIcon.set_bluetooth_status(message: str)`
   (stores it, exposes it via a new disabled menu action beneath the
   existing `_device_action`, following that action's exact
   `_disabled_action(...)` pattern — no notification popup needed here,
   unlike `bind_failed`, since Bluetooth routing is best-effort/expected
   to sometimes fail and a persistent popup per attempt would be noisy).
   Wire `hfp_manager.status_changed.connect(tray.set_bluetooth_status)`
   in `app.py` next to the existing `hfp_manager.start()` call. Testable
   with the same pattern as `test_tray_icon.py`'s bind-error tests:
   assert the new action's text updates on `set_bluetooth_status(...)`
   and is hidden/absent when no status has ever been received yet.

*(previous PM cycle's 2 items follow, still open, renumbered)*

4. **Desktop notification on incoming call, not just the popup.**
   `app.py`'s `on_state_changed` already calls `popup.show_call(...)` on
   `CallPhase.RINGING`, but if the popup window is obscured, on another
   workspace, or the compositor doesn't raise it reliably, there's no
   secondary signal. `QSystemTrayIcon.showMessage()` (already available
   on the existing `TrayIcon` instance in `ui/tray_icon.py`, confirmed
   callable without raising under the offscreen test platform this
   cycle) can fire alongside `show_call()` with the caller name/number,
   giving a second, OS-native notification path that survives even if
   the frameless popup itself is missed. Small change to `app.py`'s
   `on_state_changed` plus one new tiny method on `TrayIcon` (e.g.
   `notify_incoming_call(name, number)`); testable by asserting the tray
   method is invoked with the right args (mock/spy), same pattern as the
   existing state-controller tests — no real OS notification daemon
   needed for the unit test.
5. **"Copy this device's address" tray action.** `network/local_address.py`'s
   `device_label()` is shown today only as a disabled/inert menu item in
   `ui/tray_icon.py` (`self._device_action = self._disabled_action(device_label)`)
   — the user must manually retype the IP:port into the Android app,
   error-prone on a phone keyboard. Add a small enabled `QAction` ("Copy
   Address") beneath it that puts the `host:port` string on the clipboard
   via `QGuiApplication.clipboard().setText(...)` (confirmed working
   under `QT_QPA_PLATFORM=offscreen` this cycle — clipboard set/readback
   round-tripped correctly in a throwaway test). Pure-logic part (parsing
   `device_label()`'s `"This device: <ip>:<port>"` down to just the
   copyable `<ip>:<port>` token, so a "no network connection" label isn't
   copied verbatim) can be a standalone helper function in
   `network/local_address.py` and unit tested with plain string fixtures,
   no Qt/clipboard needed for that part.

*(older, still-open ideas from the previous seed batch follow — kept in
the same "Proposed" section per the format the Engineer persona expects)*

6. **Reconnect banner in the call popup.** `ui/call_popup.py` /
   `network/call_server.py`: when `connection_changed` emits `False`
   while a call is active, the popup currently has no visual indicator
   the phone link dropped. Add a small "Phone disconnected" banner state.
7. **Tray icon: show device label on hover only, status in bold.**
   `ui/tray_icon.py`'s `_status_label()` currently always shows the same
   plain menu item. Minor UX polish, small + safe to try first as a
   warm-up.
8. **Config file for port override.** `network/call_server.py` hardcodes
   `DEFAULT_PORT = 8765`. Add optional `~/.config/dash-phonecon/config.json`
   read (port override only, default unchanged) so a user with a port
   conflict isn't stuck. Additive, no protocol change.
9. **Structured logging: log connection duration on disconnect.**
   `network/call_server.py`'s `_handle_client` logs "Phone disconnected"
   with no context — add elapsed connection time to the log line using
   `logging_setup.py`'s existing logger. Small, test-friendly (can assert
   on log records).
10. **`CallState` history / last-call summary.** `state/call_state.py` +
   `state/call_state_controller.py`: track the last N call events
   in-memory (caller name/number, duration, timestamp) purely for the
   tray dropdown ("Last call: John Doe, 2m 14s ago") — no persistence
   required, keep it simple.

## Shipped

*(engineer persona appends here, format: `- [SHA] feat: description
  (timestamp)`)*

- [7490f21] feat: surface `bind_failed` to the tray icon instead of dropping it silently (2026-07-10 02:56 IST)

## Abandoned

*(engineer persona appends here, format: `- feat: description — reason
  (timestamp)`)*
