# Overnight Auto-Research Backlog

Shared file between the BA/PM persona (adds to Proposed) and the Engineer
persona (moves Proposed -> Shipped or Abandoned). Newest proposals go at
the TOP of their section. Read `.overnight/GUARDRAILS.md` before touching
this file or the codebase.

## Proposed

*(PM cycle 2026-07-10 ~02:44 IST added the 3 items below to the top —
grounded in a fresh read of the current linux/ source, see state.md for
the rationale on each)*

1. **Desktop notification on incoming call, not just the popup.**
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
2. **"Copy this device's address" tray action.** `network/local_address.py`'s
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

3. **Reconnect banner in the call popup.** `ui/call_popup.py` /
   `network/call_server.py`: when `connection_changed` emits `False`
   while a call is active, the popup currently has no visual indicator
   the phone link dropped. Add a small "Phone disconnected" banner state.
4. **Tray icon: show device label on hover only, status in bold.**
   `ui/tray_icon.py`'s `_status_label()` currently always shows the same
   plain menu item. Minor UX polish, small + safe to try first as a
   warm-up.
5. **Config file for port override.** `network/call_server.py` hardcodes
   `DEFAULT_PORT = 8765`. Add optional `~/.config/dash-phonecon/config.json`
   read (port override only, default unchanged) so a user with a port
   conflict isn't stuck. Additive, no protocol change.
6. **Structured logging: log connection duration on disconnect.**
   `network/call_server.py`'s `_handle_client` logs "Phone disconnected"
   with no context — add elapsed connection time to the log line using
   `logging_setup.py`'s existing logger. Small, test-friendly (can assert
   on log records).
7. **`CallState` history / last-call summary.** `state/call_state.py` +
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
