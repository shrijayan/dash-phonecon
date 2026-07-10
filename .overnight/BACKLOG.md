# Overnight Auto-Research Backlog

Shared file between the BA/PM persona (adds to Proposed) and the Engineer
persona (moves Proposed -> Shipped or Abandoned). Newest proposals go at
the TOP of their section. Read `.overnight/GUARDRAILS.md` before touching
this file or the codebase.

## Proposed

*(PM cycle 2026-07-10 ~12:xx IST added the 3 items below to the top —
grounded in a fresh re-read of `bluetooth/hfp_manager.py`,
`logging_setup.py`/`ui/tray_icon.py`, and `state/call_state_controller.py`
against the current Proposed/Shipped/Abandoned lists; none of these
duplicate the 31 open items or any shipped/abandoned entry — in
particular item 1 below is deliberately distinct from the already-open
"retry transient `pactl` `TimeoutExpired`" idea further down (that one
adds retries for a genuinely transient failure inside `_run_pactl()`;
item 1 here instead stops *repeating* an already-permanent failure across
`_attempt_switch()`'s outer 20-attempt loop), and item 2 is distinct from
the already-shipped "Open Log File" action (that one opens the existing
file; item 2 clears its contents) and item 3 is distinct from every
existing call-duration/tally/decline-related Proposed item since it's
about a *second* incoming call arriving before the first one resolves,
not about the first call's own lifecycle.)*

1. **"Clear Log File" tray action alongside the existing "Open Log
   File" one.** Confirmed via reading `logging_setup.py` and
   `ui/tray_icon.py` that the rotating file handler
   (`RotatingFileHandler(..., maxBytes=1_000_000, backupCount=3)`) has no
   user-facing way to reset it — the only options today are "Open Log
   File" (read-only) or manually deleting files by hand in
   `$XDG_STATE_HOME/dash-phonecon/`, which most users won't know to do,
   so a user trying to capture a *fresh* debug session (e.g. after
   reproducing a Bluetooth routing issue per the README's troubleshooting
   flow) has to wade through old unrelated log history. Add a small
   `logging_setup.clear_log_file() -> None` that truncates
   `log_file_path()` in place (open in `"w"` mode, matching the exact
   truncation semantics `RotatingFileHandler` itself would use on
   rollover — no need to touch the `.1`/`.2`/`.3` backups, those age out
   naturally), and a new `QAction("Clear Log File")` beside
   `self._open_log_action` in `ui/tray_icon.py` wired the same way (new
   `on_clear_log: Callable[[], None] | None` constructor param), called
   from `app.py` via `lambda: logging_setup.clear_log_file()`. Testable
   directly in the existing `linux/tests/test_logging_setup.py` (already
   has an `XDG_STATE_HOME` override/fallback pattern from the "Open Log
   File" cycle) by writing known content, calling `clear_log_file()`,
   and asserting the file exists and is empty, plus a
   `test_tray_icon.py` case asserting the new action's callback fires on
   trigger.
3. **Log when a new `CALL_RINGING` arrives while a previous call is
   still `RINGING` or `ACTIVE` (a second incoming call before the first
   resolved).** Confirmed via reading
   `state/call_state_controller.py`'s `handle_event()` that the
   `CALL_RINGING` branch unconditionally calls `self._set_state(...)`,
   silently overwriting whatever call state was already there — a real,
   observable phone-side scenario (call waiting, or a stale/duplicate
   `CALL_RINGING` replay from a flaky connection arriving after the
   user already answered) leaves zero trace in the log of the fact that
   one call's state was discarded in favor of another, making a user
   report like "my active call just silently vanished" undiagnosable
   from the log file alone. Add a guard right before the existing
   `logger.info("Call ringing: ...")` line: if
   `self._state.phase is not CallPhase.IDLE`, log a
   `logger.warning("New call ringing (%s) while previous call was %s (%s) - overwriting previous call state", ...)` 
   instead of (or in addition to) the existing info line, using
   `self._state.phase.name` and `self._state.display_name` for the
   previous call's identity. Testable directly in
   `linux/tests/test_call_state.py` (already has an
   `assertLogs`-based pattern from the missed-call tests) with a
   `RINGING → CALL_RINGING` (or `ACTIVE → CALL_RINGING`) transition
   sequence asserting the new `WARNING` record appears, and a plain
   `IDLE → CALL_RINGING` transition asserting it does not.

*(PM cycle 2026-07-10 ~11:xx IST added the 3 items below to the top —
grounded in a fresh re-read of `network/call_server.py`,
`bluetooth/bluez_device_finder.py`, and `media_ducker.py` against the
current Proposed/Shipped/Abandoned lists; none of these duplicate the 28
open items or any shipped/abandoned entry.)*

1. **Filter out `Blocked` Bluetooth devices in
   `bluez_device_finder.paired_phones()`.** Confirmed via reading BlueZ's
   `org.bluez.Device1` interface (and this file's own `_to_phone()`) that
   a device the user has explicitly blocked via `bluetoothctl block
   <mac>` (or their desktop Bluetooth settings) still reports `Paired:
   true` and the same `Class`/phone-detection bits — `paired_phones()`
   only checks `Paired`, never `Blocked`, so a phone the user
   deliberately blacklisted from connecting can still be selected by
   `find_paired_phone()` and have call audio silently routed to/from it,
   directly contradicting the user's explicit block action. Add
   `if bool(device.get("Blocked", False)): continue` right alongside the
   existing `Paired`/`Class` checks in the `for interfaces in
   managed_objects.values():` loop. Testable directly in a new
   `linux/tests/test_bluez_device_finder.py` (check if one already
   exists first — none did as of this cycle) using plain dict fixtures
   for `managed_objects` (no real D-Bus needed, mirrors the existing
   `test_audio_router_parsing.py` pattern): a blocked-but-paired phone
   dict is excluded from `paired_phones()`'s result; an unblocked one is
   still included.
3. **Guard `MediaDucker.duck_others()`'s `list_player_services(bus)` call
   against a mid-scan `DBusException`.** Confirmed via reading
   `media_ducker.py` that `duck_others()` wraps only the initial
   `dbus.SessionBus()` construction in `try/except DBusException`, but
   the very next line, `for service_name in list_player_services(bus):`,
   calls `bus.list_names()` with no exception handling at all — if the
   session bus becomes unreachable *between* `SessionBus()` succeeding
   and `list_names()` being called (e.g. the D-Bus daemon restarts
   mid-call-setup, a real if rare timing window), this raises an
   uncaught `DBusException` straight out of `duck_others()`, which
   `app.py`'s `on_state_changed` calls synchronously from a Qt signal
   handler — an uncaught exception there is a much worse failure mode
   than the "best-effort, never breaks the call" philosophy this same
   module's docstring promises (`get_playback_status`/`pause_player`
   already individually catch `DBusException`, just not this one call
   site). Wrap the `list_player_services(bus)` call (or the whole loop)
   in the same `try/except DBusException` pattern already used two
   lines above, logging via `logger.info` and returning early exactly
   like the existing `SessionBus()` failure branch does. Testable
   directly in `linux/tests/test_media_ducker.py` by making the fake
   bus's `list_names` raise `DBusException` (extend `_fake_bus` with an
   optional `list_names_error` param) and asserting `duck_others()`
   does not raise — same "must not raise" assertion style the existing
   `test_duck_others_disabled_gracefully_when_session_bus_unreachable`
   test already uses for the `SessionBus()` failure case.

*(PM cycle 2026-07-10 ~10:xx IST added the 3 items below to the top —
grounded in a fresh re-read of `bluetooth/hfp_manager.py`,
`state/call_state_controller.py`, and `bluetooth/audio_router.py` against
the current Proposed/Shipped/Abandoned lists; none of these duplicate the
25 open items or any shipped/abandoned entry — in particular item 1 below
is deliberately distinct from the already-open "Manual Rescan for Paired
Phone" tray action (that one is a user-triggered re-scan at any later
time; item 1 is an *automatic*, bounded startup-only retry to survive a
login-session race with `bluetoothd`), and item 3 below is distinct from
the already-open `bind_with_retries`-style ideas since it targets
`pactl` subprocess calls, not the WebSocket bind.)*

1. **Log the elapsed call duration when a call that was actually
   answered ends.** Confirmed via reading
   `state/call_state_controller.py`'s `handle_event()` that the
   `CALL_ENDED` branch only logs the bare string `"Call ended"` — for a
   call that reached `CallPhase.ACTIVE` (i.e. was answered, not a missed
   call, which is already handled by the existing `call_missed` signal),
   `self._state.start_time` is sitting right there unused, so there is
   no way to tell from the log alone how long a given call lasted
   without cross-referencing the RINGING/ACTIVE/ENDED timestamps by
   hand. Add a branch alongside the existing `phase is CallPhase.RINGING`
   check: `elif self._state.phase is CallPhase.ACTIVE and
   self._state.start_time is not None: logger.info("Call ended after %s",
   ...)` using `datetime.now() - self._state.start_time`. Testable
   directly in `linux/tests/test_call_state.py` with `assertLogs`,
   following the exact same `RINGING → CALL_ENDED` /
   `RINGING → ACTIVE → CALL_ENDED` test-state-machine pattern the
   existing `call_missed` tests already use — just asserting on the log
   record text/level instead of (or in addition to) the signal.
3. **Retry transient `pactl` failures in `bluetooth/audio_router.py`
   instead of failing the whole switch attempt on one blip.** Confirmed
   via reading `audio_router.py`'s `_run_pactl()` that any non-zero
   `pactl` exit code or `subprocess.TimeoutExpired` immediately raises
   `AudioRouterError`, which `hfp_manager.py`'s `_try_switch_now()`
   treats as "not ready yet, retry via the outer `_attempt_switch` loop
   in ~1s" — functionally fine, but every single-blip PipeWire hiccup
   (e.g. `pactl` momentarily can't reach a busy PipeWire daemon right as
   Bluetooth profile negotiation finishes) burns a full attempt out of
   the already-bounded `_MAX_ATTEMPTS = 20`, tightening the real
   ~20-second window `hfp_manager.py`'s docstring/comments describe.
   Add a small `run_with_retries(fn, attempts=2, delay=0.2)` free
   function in `audio_router.py` (same shape/spirit as
   `network/call_server.py`'s already-shipped `bind_with_retries`, but
   for a plain sync callable instead of an async one) and wrap just the
   `_run_pactl()` call site's `subprocess.run` invocation with it, only
   retrying on `subprocess.TimeoutExpired` (a real transient signal), not
   on a non-zero exit code (a real, stable failure like "not paired").
   Testable directly and cheaply in a new
   `linux/tests/test_audio_router_retry.py` with a fake callable that
   raises `TimeoutExpired` once then returns — mirrors the existing
   `test_call_server_bind_retry.py` test shape exactly, no real `pactl`
   binary needed.

*(PM cycle 2026-07-10 ~09:xx IST added the 3 items below to the top —
grounded in a fresh re-read of `network/call_server.py`,
`bluetooth/bluez_device_finder.py`, and `network/local_address.py`
against the current Proposed/Shipped/Abandoned lists; none of these
duplicate the 22 open items or any shipped/abandoned entry — in
particular this is deliberately distinct from the already-open
`--port`/`-p` CLI flag idea (that one is about *choosing* the port,
item 1 below is about *knowing when the server actually started
listening on it*) and from the already-open "Rescan for Paired Phone"
action (that one re-runs discovery on demand; item 2 below fixes a
determinism bug in the discovery result itself, independent of when
it's triggered).)*

1. **Make `bluez_device_finder.find_paired_phone()`'s tie-break
   deterministic when multiple paired phones exist and none are
   currently connected.** Confirmed via reading `paired_phones()` +
   `find_paired_phone()` in `bluetooth/bluez_device_finder.py` that
   `phones.sort(key=lambda phone: phone.connected, reverse=True)` only
   orders by the boolean `connected` flag — when zero phones are
   connected (the common case right after boot, before the user's
   phone Bluetooth radio has reconnected), Python's stable sort leaves
   ties in whatever order `manager.GetManagedObjects().values()`
   iterated them, which is BlueZ's D-Bus dict ordering, not guaranteed
   stable across daemon restarts or after (un)pairing other devices —
   so on a machine paired with more than one phone, which one gets
   picked for call-audio routing can silently change between app
   restarts with no user-visible reason. Add a secondary sort key on
   `phone.name` (case-insensitive) so the result is deterministic and
   documented, e.g. `phones.sort(key=lambda phone: (not phone.connected,
   phone.name.lower()))`. Testable directly in a
   new/expanded `linux/tests/test_bluez_device_finder.py`-style test
   (check if one already exists first) with plain `BluetoothPhone`
   fixtures — no real D-Bus/BlueZ needed, mirrors the existing
   `test_audio_router_parsing.py` pattern of testing pure logic against
   plain dict/dataclass fixtures.
3. **Fall back through multiple local IPs in `device_label()` instead
   of trusting a single UDP-connect route guess.** Confirmed via
   reading `network/local_address.py`'s `local_ip_address()` that it
   opens exactly one UDP socket "connected" to `8.8.8.8:80` and reports
   whichever interface the OS routing table picks for that destination
   — on a laptop with an active VPN/Tailscale interface (explicitly
   called out as a supported connectivity path in this same file's
   module docstring: "the phone connects over LAN/Tailscale"), the
   default route for an internet-bound probe can be the VPN tunnel
   interface, not the LAN Wi-Fi/Ethernet interface the phone is
   actually reachable on — so the address shown in the tray ("type this
   into the Android app") can be one the phone can never actually
   reach, with no fallback and no indication anything is wrong. Add a
   small `socket.getaddrinfo`/`socket.if_nameindex`-based enumeration
   helper (or, simpler and more testable, accept an injectable list of
   "probe hosts" tried in order, e.g. `8.8.8.8` then a private
   `192.168.0.1`-style RFC1918 gateway guess) so a VPN-only result isn't
   the sole answer silently trusted. Testable in a new
   `linux/tests/test_local_address.py` by monkeypatching the probe
   socket's `getsockname()` return value across multiple simulated
   attempts and asserting the fallback logic picks a private
   (192.168.x.x/10.x.x.x/172.16-31.x.x) address over a public/VPN one
   when both are available — no real network needed.

*(PM cycle 2026-07-10 ~08:xx IST added the 3 items below to the top —
grounded in a fresh re-read of `bluetooth/hfp_manager.py`,
`ui/tray_icon.py`, `state/call_state.py`, and
`state/call_state_controller.py` against the current
Proposed/Shipped/Abandoned lists; none of these duplicate the 19 open
items or any shipped/abandoned entry — in particular this is
deliberately distinct from the already-open "Duck Media During Calls"
toggle (that one gates `media_ducker.py`; item 1 below gates
`hfp_manager.py`, a different subsystem with its own opt-out gap) and
from the already-open "Rescan for Paired Phone" action.)*

2. **Extract a pure `format_call_duration(seconds: int) -> str` helper
   into `state/call_state.py`, used by `ui/tray_icon.py`'s
   `_update_timer_text()`.** Confirmed via reading both files that the
   `minutes, seconds = divmod(elapsed, 60); f"{minutes:02d}:{seconds:02d}"`
   formatting logic lives inline inside `TrayIcon._update_timer_text()`
   with zero direct unit-test coverage of the formatting math itself
   (existing `test_tray_icon.py` tests only cover visibility/wiring, not
   the numeric-to-string conversion for edge cases like 0 seconds, exactly
   60 seconds, or anything past 59:59 e.g. a 65-minute call — `>59` minutes
   currently just keeps growing the minutes field unbounded, which is
   probably fine but is currently untested/undocumented behavior). Move
   the one-line formula into `state/call_state.py` as a standalone
   function (no Qt import needed, keeping it in the already-Qt-free
   state module per that file's own module docstring philosophy), have
   `_update_timer_text()` call it. Testable directly and cheaply in
   `linux/tests/test_call_state.py` with plain integers — no Qt/display
   needed at all: `format_call_duration(0) == "00:00"`,
   `format_call_duration(65) == "01:05"`,
   `format_call_duration(3661) == "61:01"`.
3. **Deduplicate repeated "Ignoring unknown/unsupported message" log
   warnings in `CallStateController.handle_event()`.** Confirmed via
   reading `state/call_state_controller.py` that the final `else`
   branch calls `logger.warning(...)` on every single call with an
   unrecognized/missing `type` field, with no rate limiting or
   deduplication — if a future phone-side protocol version (or a flaky
   connection replaying stale bytes) sends the same unknown message
   type repeatedly, this can flood the rotating log file
   `logging_setup.py` maintains, pushing genuinely useful recent
   history (the last real call) out of the `_BACKUP_COUNT = 3`-file
   rotation window faster than it should. Add a small `_last_unknown_type: str | None`
   instance attribute; only log at `WARNING` when the unknown/missing
   type differs from the last one seen, otherwise log at `DEBUG` (still
   visible with the already-open `--verbose` flag idea for real
   debugging, just not spamming the default `INFO` log). Testable
   directly in `linux/tests/test_call_state.py` with `assertLogs`:
   two consecutive messages with the same bogus `"type"` value produce
   exactly one `WARNING` record and one `DEBUG` record; a third message
   with a *different* bogus type produces a fresh `WARNING`.

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

- [42b04f6] feat: log when a new phone connection replaces an existing one (2026-07-10 overnight cycle)
- [796eb24] feat: retry HfpManager startup scan on transient BlueZ D-Bus errors (2026-07-10 overnight cycle)
- [1fa5e70] feat: add checkable Bluetooth call-audio routing toggle to tray icon (2026-07-10 overnight cycle)
- [5114e9d] feat: surface CallServer.listening in the tray status instead of generic "Not Connected" (2026-07-10 overnight cycle)
- [d1f5539] feat: log the underlying OSError when single-instance lock acquire fails (2026-07-10 overnight cycle)
- [7490f21] feat: surface `bind_failed` to the tray icon instead of dropping it silently (2026-07-10 02:56 IST)
- [82a00f0] feat: notify on missed calls in the tray icon (2026-07-10 03:34 IST)
- [2b77c2a] feat: retry binding the WebSocket port a few times before giving up (2026-07-10 04:45 IST)
- [20c83a4] feat: refresh tray device label periodically instead of once at startup (2026-07-10 04:33 IST)
- [5bfacb7] feat: add "Open Log File" tray action (2026-07-10 cycle)
- [596ca61] feat: stop repeating pactl-not-installed warnings across HFP retry loop (2026-07-10 overnight cycle)

## Abandoned

*(engineer persona appends here, format: `- feat: description — reason
  (timestamp)`)*
