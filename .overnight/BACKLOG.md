# Overnight Auto-Research Backlog

Shared file between the BA/PM persona (adds to Proposed) and the Engineer
persona (moves Proposed -> Shipped or Abandoned). Newest proposals go at
the TOP of their section. Read `.overnight/GUARDRAILS.md` before touching
this file or the codebase.

## Proposed

*(PM cycle 2026-07-10 ~07:10 IST added the 3 items below to the top —
grounded in a fresh re-read of `single_instance.py`, `logging_setup.py`,
`network/local_address.py`, `ui/call_popup.py`, and `app.py` against the
current Proposed/Shipped/Abandoned lists; none of these duplicate the 16
open items or either shipped/abandoned entry.)*

1. **`--port`/`-p` CLI flag to override the WebSocket listen port, no
   config file needed.** `network/call_server.py` hardcodes
   `DEFAULT_PORT = 8765` and `CallServer()`'s constructor already
   accepts no port argument at all (confirmed via grep: `CallServer()`
   is instantiated with zero args in `app.py`, and nothing in the tree
   reads an env var or CLI arg for it) — so a user with something else
   already bound to 8765 has literally no way to run this app today
   short of editing source, a strictly worse experience than the
   already-Proposed config-file idea (item 7 further down) but much
   smaller in scope: just wire the port `CallServer.__init__` already
   supports (or add a trivial `port: int = DEFAULT_PORT` parameter if
   it's missing) through a small `argparse`-based `parse_args(argv:
   list[str]) -> Namespace` helper in `app.py`, mirroring the exact
   shape the already-open `-v`/`--verbose` idea further down proposes
   (both are pure-argparse, no-Qt-needed helpers — land whichever of
   the two lands first, then the second trivially extends the same
   helper instead of duplicating an `argparse.ArgumentParser()`).
   Testable in a new/extended `linux/tests/test_app_args.py`: assert
   `parse_args([]).port == 8765` and `parse_args(["-p", "9999"]).port
   == 9999` / `parse_args(["--port", "9999"]).port == 9999` — no Qt
   involved.
3. **Log and surface a warning when the call popup's `show_call()`
   fires with an off-screen or oversized computed position (multi-monitor
   edge case).** `ui/call_popup.py`'s `_move_to_top_right()` computes
   `x = available.right() - self.width() - _SCREEN_MARGIN_PX` purely
   from `QGuiApplication.primaryScreen()` — confirmed via grep this
   never checks `QGuiApplication.screens()` for the currently active/
   most-relevant screen, so on a multi-monitor setup where the primary
   screen is smaller than a secondary one (or the user's cursor/active
   window lives on a different screen), the popup can render off the
   visible primary screen area entirely if `available.right()` returns
   a stale/unexpected value, with zero logging to explain why the popup
   "never showed up." Add a tiny pure-logic helper
   `compute_popup_position(available_geometry: QRect, popup_width: int,
   margin: int) -> tuple[int, int]` extracted out of
   `_move_to_top_right()`'s existing math (no behavior change, just
   makes it independently testable), and log
   `logger.debug("Positioning call popup at (%d, %d) within screen
   %dx%d", ...)` right before `self.move(...)` so a future off-screen
   report is diagnosable from the log file the README already tells
   users to check. Testable directly in a new
   `linux/tests/test_call_popup_position.py` with plain `QRect`
   fixtures (no real screen needed) asserting the returned `(x, y)`
   matches the documented top-right-with-margin formula for a few
   width/height combinations.

*(PM cycle 2026-07-10 ~06:20 IST added the 3 items below to the top —
grounded in a fresh re-read of `logging_setup.py`, `media_ducker.py`,
`bluetooth/hfp_manager.py`, and `ui/tray_icon.py` against the current
Proposed/Shipped/Abandoned lists; none of these duplicate the 14 open
items or either shipped/abandoned entry.)*

1. **Checkable "Duck Media During Calls" tray toggle.**
   `media_ducker.py`'s `MediaDucker` is unconditionally wired in
   `app.py` today (confirmed via grep: `duck_others()`/`restore_others()`
   are always called on `CALL_ACTIVE`/`CALL_ENDED`, no way to opt out) —
   but pausing Spotify/Firefox/VLC mid-call is exactly the kind of
   "helpful most of the time, occasionally annoying" behavior (e.g. a
   user deliberately keeping music going through a Bluetooth speaker
   during a quick call) that benefits from a per-user toggle, same
   spirit as the already-shipped bind-error and missed-call surfacing
   but for opt-*out* UX rather than visibility. Add a checkable
   `QAction("Duck Media During Calls")` to `ui/tray_icon.py` (defaults
   checked, following the exact toggled-`QAction` pattern the existing
   "Start on Login" idea above also needs — reuse/validate that
   pattern once here if it lands first), wired via `on_toggle_ducking:
   Callable[[bool], None]`. In `app.py`, guard the existing
   `media_ducker.duck_others()`/`restore_others()` calls behind a
   simple `if ducking_enabled:` flag flipped by the callback — no
   change needed inside `media_ducker.py` itself. Testable in
   `test_tray_icon.py` exactly like the existing checkable-action tests
   (toggle state changes on trigger, callback invoked with the right
   bool), plus one `app.py`-level test if `app.py` already has a light
   test harness, or otherwise document as UI-only coverage in the
   commit body.
3. **Manual "Rescan for Paired Phone" tray action for Bluetooth
   audio.** `bluetooth/hfp_manager.py`'s `HfpManager.start()` docstring
   says outright "Look for a paired phone once, at app startup" —
   confirmed via grep there is no code path that ever calls
   `find_paired_phone()` again afterwards, so if the user pairs their
   phone's Bluetooth *after* launching Dash Phone Con (a very plausible
   ordering — pairing is a manual, easy-to-forget step per
   `linux/README.md`'s Bluetooth call-audio section), the only fix
   today is fully restarting the app. Add a small
   `HfpManager.rescan() -> None` public method that just re-runs the
   same body as `start()` (calls `find_paired_phone()`, updates
   `self._phone`, re-emits `status_changed` — trivial refactor: have
   `start()` call `self.rescan()` internally so there is exactly one
   implementation), and wire a new enabled `QAction("Rescan for Paired
   Phone")` in `ui/tray_icon.py` calling into it via `app.py`. Testable
   directly in a new/expanded `bluetooth/test_hfp_manager.py`-style
   test (check if one already exists first) by monkeypatching
   `find_paired_phone` to return different values on successive calls
   and asserting `rescan()` updates `self._phone` and emits the new
   status string each time — no real BlueZ/D-Bus needed, same
   mocking approach the existing HFP tests (if any) already use.

*(PM cycle 2026-07-10 ~05:10 IST added the 3 items below to the top —
grounded in a fresh re-read of `network/local_address.py`,
`network/call_server.py`, `single_instance.py`, and `app.py` against the
current Proposed/Shipped/Abandoned lists; none of these duplicate the
existing open items or either shipped feature.)*

1. **XDG "Start on Login" autostart toggle.**
   `linux/src/dashphone/` and `linux/packaging/` that nothing writes an
   XDG autostart `.desktop` entry — a user has to manually configure
   their DE's session/startup apps to have Dash Phone Con come back
   after reboot, undocumented anywhere in `linux/README.md`. Add a
   small new `autostart.py` module with pure, easily-testable functions
   `is_enabled() -> bool`, `enable() -> None`, `disable() -> None` that
   read/write `$XDG_CONFIG_HOME/autostart/dash-phonecon.desktop` (falls
   back to `~/.config/autostart/...`, same `XDG_STATE_HOME`-style
   fallback pattern already used in `logging_setup.py`'s
   `log_file_path()`). Wire a checkable `QAction("Start on Login")` in
   `ui/tray_icon.py`'s menu (new constructor param
   `on_toggle_autostart: Callable[[bool], None]`, checked state set from
   `autostart.is_enabled()` at construction) calling into `app.py`'s
   `autostart.enable()`/`disable()`. Testable end-to-end without a real
   session: point `XDG_CONFIG_HOME` at a `tempfile.TemporaryDirectory()`
   in a new `linux/tests/test_autostart.py`, assert the `.desktop` file
   is created/removed and `is_enabled()` reflects it correctly.
2. **Surface the connected phone's remote IP in the tray status
   instead of just logging it.** `network/call_server.py`'s
   `_handle_client` logs `"Phone connected from %s", connection.remote_address`
   but that address is never emitted as a signal or shown anywhere in
   the UI — confirmed via grep that `connection_changed` only carries a
   bare `bool`, no address. On a network with more than one device (or
   to sanity-check the right phone reconnected after a Wi-Fi hiccup),
   the user currently has no way to see which IP is talking to the app
   without opening the log file. Add a new
   `CallServer.phone_connected = Signal(str)` emitting
   `str(connection.remote_address[0])` (or the full tuple stringified,
   whichever `_handle_client` already has on hand) right where the
   existing `connection_changed.emit(True)` fires, and a
   `TrayIcon.set_phone_address(address: str | None)` (None clears it on
   disconnect) that appends `" (from 192.168.x.y)"` to the existing
   `_status_label()`'s "Connected" line. Testable: a new
   `test_call_server.py` case constructing a fake `ServerConnection`-like
   object with a `.remote_address` attribute and asserting
   `phone_connected` fires with the right string via `_handle_client`
   (can call the coroutine directly with `asyncio.run` against a stub
   async iterator), plus a `test_tray_icon.py` case asserting the label
   text includes/omits the address correctly.

*(PM cycle 2026-07-10 ~04:05 IST added the 3 items below to the top —
grounded in a fresh re-read of `network/call_server.py`, `__main__.py`,
`state/call_state_controller.py`, and `linux/tests/` against the current
BACKLOG/state after the missed-call ship; none of these duplicate the
9 open items or either shipped feature below.)*

1. **`--verbose`/`-v` CLI flag to enable debug logging.**
   `logging_setup.py`'s `setup_logging(verbose: bool = False)` already
   has the parameter fully wired (sets `DEBUG` vs `INFO` on the root
   logger) but `__main__.py`/`app.py`'s `main()` never exposes it —
   confirmed via grep that `setup_logging()` is only ever called with
   no arguments, so a user who needs to diagnose a Bluetooth/HFP or
   connection issue (per `linux/README.md`'s troubleshooting section)
   has no way to get debug-level detail into the log file without
   editing source. Add a tiny `argparse` parse in `app.py`'s `main()`
   (or a new small `parse_args(argv: list[str]) -> Namespace` helper,
   which is what should actually be unit tested) for `-v`/`--verbose`,
   passed through to `setup_logging(verbose=args.verbose)`. Testable by
   extracting the argument-parsing into its own pure function and
   asserting in a new `linux/tests/test_app_args.py` that
   `parse_args([])` yields `verbose=False` and `parse_args(["-v"])`/
   `parse_args(["--verbose"])` both yield `verbose=True` — no Qt
   involved at all for this part.
3. **Session call tally in the tray dropdown.** Neither
   `CallStateController` nor `TrayIcon` currently track how many calls
   happened this session — confirmed via reading both files that
   `call_missed` and the `CALL_ENDED`→answered transition are only ever
   used transiently for the immediate notification, with nothing
   accumulated. Add two plain `int` counters (`answered_count`,
   `missed_count`) to `CallStateController`, incremented in
   `handle_event`'s existing `CALL_ENDED` branch (the missed case is
   already detected there via the `phase is CallPhase.RINGING` check;
   the answered case is the `else` — `phase is CallPhase.ACTIVE`),
   exposed as read-only properties. Wire a new
   `TrayIcon.set_call_tally(answered: int, missed: int)` that updates a
   small disabled menu label (e.g. "Today: 2 answered, 1 missed",
   following the exact `_disabled_action(...)` pattern already used for
   `_device_action`), called from `app.py`'s existing `on_call_missed`
   plus a new equivalent hook for the answered-call path. Testable
   exactly like the existing `call_missed` tests in
   `test_call_state.py` (assert the counters increment on the right
   transitions and stay put on the wrong ones) plus a
   `test_tray_icon.py` case asserting the label text after
   `set_call_tally(...)`.

*(PM cycle 2026-07-10 ~03:20 IST added the 3 items below to the top —
grounded in a fresh re-read of linux/src/dashphone/ against the current
BACKLOG/state after the bind_failed ship, see state.md for the
rationale on each)*

1. **"Decline" action in the tray dropdown while ringing, not just in
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
2. **Surface `HfpManager.status_changed` in the tray instead of only
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

3. **Desktop notification on incoming call, not just the popup.**
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
4. **"Copy this device's address" tray action.** `network/local_address.py`'s
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

5. **Reconnect banner in the call popup.** `ui/call_popup.py` /
   `network/call_server.py`: when `connection_changed` emits `False`
   while a call is active, the popup currently has no visual indicator
   the phone link dropped. Add a small "Phone disconnected" banner state.
6. **Tray icon: show device label on hover only, status in bold.**
   `ui/tray_icon.py`'s `_status_label()` currently always shows the same
   plain menu item. Minor UX polish, small + safe to try first as a
   warm-up.
7. **Config file for port override.** `network/call_server.py` hardcodes
   `DEFAULT_PORT = 8765`. Add optional `~/.config/dash-phonecon/config.json`
   read (port override only, default unchanged) so a user with a port
   conflict isn't stuck. Additive, no protocol change.
8. **Structured logging: log connection duration on disconnect.**
   `network/call_server.py`'s `_handle_client` logs "Phone disconnected"
   with no context — add elapsed connection time to the log line using
   `logging_setup.py`'s existing logger. Small, test-friendly (can assert
   on log records).
9. **`CallState` history / last-call summary.** `state/call_state.py` +
   `state/call_state_controller.py`: track the last N call events
   in-memory (caller name/number, duration, timestamp) purely for the
   tray dropdown ("Last call: John Doe, 2m 14s ago") — no persistence
   required, keep it simple.

## Shipped

*(engineer persona appends here, format: `- [SHA] feat: description
  (timestamp)`)*

- [d1f5539] feat: log the underlying OSError when single-instance lock acquire fails (2026-07-10 overnight cycle)
- [7490f21] feat: surface `bind_failed` to the tray icon instead of dropping it silently (2026-07-10 02:56 IST)
- [82a00f0] feat: notify on missed calls in the tray icon (2026-07-10 03:34 IST)
- [2b77c2a] feat: retry binding the WebSocket port a few times before giving up (2026-07-10 04:45 IST)
- [20c83a4] feat: refresh tray device label periodically instead of once at startup (2026-07-10 04:33 IST)
- [5bfacb7] feat: add "Open Log File" tray action (2026-07-10 cycle)

## Abandoned

*(engineer persona appends here, format: `- feat: description — reason
  (timestamp)`)*
