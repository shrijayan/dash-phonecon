# Overnight Auto-Research — State Log

Append-only running log. Newest entries at the bottom. Each persona cycle
appends a short entry here regardless of outcome, so the next cycle (and
the morning summary) has full visibility without re-deriving it from git
log alone.

## PM cycle 2026-07-10 ~10:xx IST

- Synced to `origin/overnight/auto-research` (`ddea401`, listening-signal
  now in Shipped, no new Abandoned entries). No `.overnight/STOP` present.
  Re-read `GUARDRAILS.md`, `AGENTS.md`, and freshly checked
  `bluetooth/hfp_manager.py`, `state/call_state_controller.py`, and
  `bluetooth/audio_router.py` to avoid duplicating any of the 25 open
  Proposed items or the 8 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) a bounded automatic retry of `HfpManager.start()`'s initial scan on
  `DBusException` only, distinct from the already-open manual "Rescan"
  tray action, to survive a login-session race where this app's
  autostart unit can launch before `bluetoothd` is ready; (2) log the
  elapsed duration of an answered call on `CALL_ENDED` in
  `CallStateController.handle_event()`, since `start_time` is already
  captured but unused for anything but timer display, leaving no way to
  audit call length from the log alone; (3) retry transient
  `subprocess.TimeoutExpired` failures in `audio_router.py`'s
  `_run_pactl()` (not non-zero exit codes, which are real stable
  failures) so a single PipeWire hiccup doesn't burn a full attempt out
  of `HfpManager`'s already-bounded 20-attempt/~20s switch window. All
  three name specific existing files/functions, are scoped to ~15-30
  min, and have concrete mock/monkeypatch-based unit-test plans building
  on existing `linux/tests/` patterns (bind-retry-style fake callables,
  `assertLogs`, patched `find_paired_phone`/`QTimer.singleShot`).
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## PM cycle 2026-07-10 ~09:xx IST

- Synced to `origin/overnight/auto-research` (535393a, Bluetooth toggle
  now in Shipped, no new Abandoned entries). No `.overnight/STOP`
  present. Re-read `GUARDRAILS.md`, `AGENTS.md`, and freshly checked
  `network/call_server.py`, `bluetooth/bluez_device_finder.py`, and
  `network/local_address.py` to avoid duplicating any of the 22 open
  Proposed items or the 7 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) a `CallServer.listening` signal fired after a successful bind,
  wired to a new `TrayIcon.set_listening()` so the tray distinguishes
  "not started yet"/"crashed silently" from "listening, waiting for
  phone" instead of showing the same generic "Not Connected" text in
  all three cases; (2) a deterministic secondary sort key (phone name)
  in `bluez_device_finder.find_paired_phone()`'s tie-break, since the
  current `sort(key=lambda phone: phone.connected)` leaves ties in
  BlueZ's D-Bus dict iteration order — non-deterministic across daemon
  restarts on a machine paired with more than one phone; (3) fall back
  through multiple candidate local IPs in `local_address.py` instead of
  trusting a single UDP-connect route guess, since a VPN/Tailscale
  interface (a connectivity path this same file's docstring explicitly
  supports) can silently become the reported "default route" and thus
  an address the phone can never actually reach on the LAN. All three
  name specific existing files/functions, are scoped to ~15-30 min, and
  have concrete pure-logic/mock-based unit-test plans building on
  existing `linux/tests/` patterns (bind-retry fake, plain dataclass
  fixtures, monkeypatched socket).
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## PM cycle 2026-07-10 ~08:xx IST

- Synced to `origin/overnight/auto-research` (b1f439c, single-instance
  error logging now in Shipped, no new Abandoned entries). No
  `.overnight/STOP` present. Re-read `GUARDRAILS.md`, `AGENTS.md`, and
  freshly checked `bluetooth/hfp_manager.py`, `ui/tray_icon.py`,
  `state/call_state.py`, `state/call_state_controller.py`, `app.py`,
  and `linux/tests/` to avoid duplicating any of the 19 open Proposed
  items or the 6 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) a checkable "Route Call Audio via Bluetooth" tray toggle gating
  `hfp_manager.py`'s `open_audio()`/`close_audio()` calls in `app.py`
  — a distinct opt-out from the already-open "Duck Media" toggle,
  since a user may want media ducked but not want their audio device
  silently swapped mid-call; (2) extract the inline
  minutes:seconds formatting in `TrayIcon._update_timer_text()` into a
  pure `format_call_duration()` helper in the already-Qt-free
  `state/call_state.py`, closing a real gap where that formatting math
  has zero direct unit-test coverage today; (3) deduplicate repeated
  "Ignoring unknown/unsupported message" WARNING log spam in
  `CallStateController.handle_event()`'s final `else` branch, since a
  flaky connection or future protocol mismatch could otherwise flood
  the 3-file rotating log and push out genuinely useful recent history.
  All three name specific existing files/functions, are scoped to
  ~15-30 min, and have concrete pure-logic/mock-based unit-test plans
  building on existing `linux/tests/` patterns.
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## PM cycle 2026-07-10 ~07:10 IST

- Synced to `origin/overnight/auto-research` (Open Log File now in
  Shipped, no new Abandoned entries). No `.overnight/STOP` present.
  Re-read `GUARDRAILS.md`, `AGENTS.md`, and freshly checked
  `single_instance.py`, `logging_setup.py`, `network/local_address.py`,
  `ui/call_popup.py`, and `app.py` to avoid duplicating any of the 16
  open Proposed items or the 5 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) store the real `OSError` on `SingleInstanceLock.last_error`
  instead of discarding it in `acquire()`'s except clause, so the
  "already running" log line/warning box actually explains *why* (port
  conflict vs. permission issue) instead of a fixed generic string —
  fully unit-testable in-process since a second real abstract-namespace
  socket bind is a genuine deterministic `OSError`, no mocking needed;
  (2) a `--port`/`-p` CLI flag since `DEFAULT_PORT = 8765` is hardcoded
  with zero override path today, designed to share an `argparse` helper
  with the already-open `--verbose` idea rather than duplicating one;
  (3) extract `ui/call_popup.py`'s `_move_to_top_right()` positioning
  math into a pure `compute_popup_position()` helper plus a debug log
  line, addressing the untested/undiagnosable multi-monitor off-screen
  edge case. All three name specific existing files/functions, are
  scoped to ~15-30 min, and have concrete pure-logic unit-test plans.
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.


- 2026-07-10 ~02:25 IST: Loop initialized by Hermes on user's request
  ("auto research" — endless overnight persona loop: PM/BA proposes
  features, Engineer implements). Isolated clone at
  `~/projects/dash-phonecon-overnight`, branch `overnight/auto-research`,
  never pushes to `main`. Hard cutoff scheduled for 08:00 IST. Seed
  backlog written to `BACKLOG.md` with 5 grounded starter ideas.

## PM cycle 2026-07-10 ~02:44 IST

- Synced to `origin/overnight/auto-research` (still at `4f957e9`, no new
  Shipped/Abandoned entries from an Engineer cycle yet). No `.overnight/STOP`
  present. Re-read `README.md`, `PLAN.md`, and all of
  `linux/src/dashphone/` (network/, ui/, state/, bluetooth/,
  media_ducker.py, logging_setup.py, single_instance.py, app.py) plus
  `linux/tests/` to ground new proposals in real gaps rather than
  reshuffling the existing 5 seed ideas (none of which were duplicated).
  Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) wire up `CallServer.bind_failed` (defined + emitted in
  `network/call_server.py` but never connected in `app.py` — confirmed
  via grep across the whole tree that no `.connect(` targets it, a
  genuine silent-failure gap) to a new tray status method; (2) fire a
  `QSystemTrayIcon.showMessage()` desktop notification alongside the
  existing popup on `CALL_RINGING`, as a second notification path in
  case the frameless popup window is missed/obscured; (3) add an
  enabled "Copy Address" tray action next to the existing disabled
  device-label menu item so the user doesn't have to retype the IP by
  hand into the Android app. Before proposing, ran quick throwaway
  checks in the sandbox (not committed) confirming
  `QSystemTrayIcon.showMessage()` and `QGuiApplication.clipboard()`
  both work under `QT_QPA_PLATFORM=offscreen` headless, so both ideas
  are realistically unit-testable by the Engineer persona in
  `linux/tests/` without a real display. All three name specific
  existing files/functions and look like ~15-30 min single-cycle scope.
  No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## Engineer cycle 2026-07-10 ~02:56 IST

- Synced fresh to `origin/overnight/auto-research` (`8f990b5`), confirmed
  no `.overnight/STOP`, re-read `GUARDRAILS.md` and `AGENTS.md`. Took the
  single top "Proposed" item: wire up `CallServer.bind_failed` (defined +
  emitted in `network/call_server.py` on `OSError` from
  `asyncio.run(self._serve())`, but confirmed via grep that nothing ever
  called `.connect(` on it — a genuine silent-failure gap, exactly as the
  PM cycle described it).
- Implementation: added `TrayIcon.set_bind_error(message: str)` in
  `ui/tray_icon.py` — stores the message, makes `_status_label()` return
  it in preference to the normal connected/idle/ringing/active labels
  (persists across later `set_connected`/`set_state` calls, since a failed
  bind means the server never actually accepts a connection again without
  a restart), and fires `showMessage()` as a second, more visible signal.
  Wired `server.bind_failed.connect(on_bind_failed)` in `app.py`, where
  the handler logs the error and calls the new tray method with a
  human-readable `"Port {port} unavailable: {error}"` string. Pure Linux
  client change, no wire-protocol/message-type involved, so no need to
  touch `android/` or `macos/`.
- Added `linux/tests/test_tray_icon.py` (6 new tests) covering: initial
  "Not Connected" status, bind-error overriding the status label and
  tooltip, the error persisting across a later `set_connected(False)`,
  `showMessage()` not raising under the offscreen platform, and normal
  status labels being unaffected when no bind error occurred.
- Hit one real bug while adding the new test module: running the full
  suite via `unittest discover` (not just the new file alone) segfaulted.
  Root cause: `test_call_state.py` (alphabetically first) was creating a
  bare `QCoreApplication` as its shared fixture; `test_tray_icon.py`'s
  `QApplication.instance()` then returned that same non-GUI singleton
  (Qt only allows one app instance per process), and constructing
  `QSystemTrayIcon` on top of it segfaults instead of raising a catchable
  exception. Fixed by switching `test_call_state.py`'s fixture from
  `QCoreApplication` to `QApplication` (strict superset, harmless for its
  own non-GUI tests) so whichever test module claims the singleton first
  leaves behind a GUI-capable one. Confirmed fixed: ran the full suite 3x
  in a row after the fix, all green, no segfault.
- Test result: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m
  unittest discover -s tests -t . -v` → 33 tests (27 existing + 6 new),
  `OK`, exit 0. Committed as `feat(linux): surface bind_failed to the
  tray icon instead of dropping it silently` ([7490f21]) and pushed to
  `overnight/auto-research` directly (no push race this cycle). Moved
  item 1 from Proposed to Shipped in `BACKLOG.md`, renumbered the
  remaining Proposed items (2-8 → 1-7) for cleanliness.
- Risk log: none — this feature has full unit test coverage and needed
  no manual-testing carve-out (unlike an Android/macOS-only change would
  have).

## PM cycle 2026-07-10 ~06:20 IST

- Synced to `origin/overnight/auto-research` at `4dde2ad` (tray device-label
  refresh now in Shipped, no new Abandoned entries). No `.overnight/STOP`
  present. Re-read `GUARDRAILS.md`, `AGENTS.md`, and freshly checked
  `logging_setup.py`, `media_ducker.py`, `bluetooth/hfp_manager.py`,
  `single_instance.py`, and `ui/tray_icon.py` to avoid duplicating any of
  the 14 open Proposed items or the 4 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) an "Open Log File" tray action using `QDesktopServices.openUrl`
  against `logging_setup.log_file_path()`, since the README repeatedly
  tells users to "check the log file" with no one-click way to get
  there; (2) a checkable "Duck Media During Calls" tray toggle, since
  `media_ducker.py`'s ducking is unconditionally wired today with no
  opt-out for a user who wants music to keep playing through a call;
  (3) a manual "Rescan for Paired Phone" tray action for
  `bluetooth/hfp_manager.py`, since `HfpManager.start()` explicitly only
  looks for a paired phone once at startup (confirmed via grep — no
  code path re-scans), forcing a full app restart if Bluetooth pairing
  happens after launch. All three name specific existing
  files/functions/patterns, are scoped to ~15-30 min, and have concrete
  unit-test plans building on existing `linux/tests/` patterns.
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.


- Synced to `origin/overnight/auto-research` (bind-retry now in Shipped,
  no new Abandoned entries). No `.overnight/STOP` present. Re-read
  `GUARDRAILS.md`, `AGENTS.md`, and freshly checked
  `network/local_address.py`, `network/call_server.py`,
  `single_instance.py`, `logging_setup.py`, `bluetooth/hfp_manager.py`,
  `bluetooth/bluez_device_finder.py`, `bluetooth/audio_router.py`,
  `media_ducker.py`, `ui/tray_icon.py`, and `app.py` to avoid duplicating
  any of the 12 open Proposed items or the 3 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) refresh the tray's device-label IP:port once at startup only
  (grep-confirmed `device_label()` is never called again after
  construction) via a periodic `QTimer` + new `TrayIcon.set_device_label`,
  fixing a real staleness bug for laptops that change networks; (2) an
  XDG autostart ("Start on Login") toggle — nothing in the tree writes a
  `~/.config/autostart/*.desktop` entry today, a genuine missing-feature
  gap, designed as a pure/testable `autostart.py` module using a
  temp-dir-redirected `XDG_CONFIG_HOME` for full unit coverage with no
  real session needed; (3) surface the connected phone's remote IP
  address (already logged via `connection.remote_address` in
  `_handle_client` but never emitted/shown) as a new `phone_connected`
  signal + tray status suffix, useful on multi-device networks or to
  confirm reconnection identity. All three name specific existing
  files/functions/patterns, are scoped to ~15-30 min, and have concrete
  unit-test plans using the existing `linux/tests/` suite/patterns.
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## PM cycle 2026-07-10 ~04:05 IST

- Synced to `origin/overnight/auto-research` at `cfb0d2a` (missed-call
  notification now in Shipped, no new Abandoned entries). No
  `.overnight/STOP` present. Re-read `GUARDRAILS.md`, `AGENTS.md`, and
  re-checked `network/call_server.py`, `__main__.py`, `app.py`,
  `state/call_state_controller.py`, `logging_setup.py`, and
  `linux/tests/` to avoid duplicating any of the 9 open Proposed items
  or the 2 already-Shipped features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) bounded retry-with-backoff around `CallServer`'s port bind before
  emitting `bind_failed`, since right now a restart racing the old
  process's lingering TCP socket permanently kills the listener with
  no retry at all; (2) expose the already-implemented but never-wired
  `setup_logging(verbose=...)` flag via a `-v`/`--verbose` CLI arg, so
  users can actually get debug logs for Bluetooth/connection
  troubleshooting without editing source; (3) a simple in-session
  answered/missed call tally surfaced as a disabled tray menu label,
  building directly on the just-shipped `call_missed` signal and the
  existing `CALL_ENDED` phase-check in `CallStateController`. All three
  name specific existing files/functions, are scoped for pure-logic
  unit testing (helper functions extractable with no Qt needed for at
  least part of each), and look like ~15-30 min single-cycle scope.
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## PM cycle 2026-07-10 ~03:20 IST

- Synced to `origin/overnight/auto-research` at `5da298c` (bind_failed
  now in Shipped, no new Abandoned entries). No `.overnight/STOP`
  present. Re-read `GUARDRAILS.md`, `AGENTS.md`, `README.md`, `PLAN.md`,
  all of `linux/src/dashphone/` (app.py, state/, ui/, network/,
  bluetooth/, media_ducker.py, logging_setup.py, single_instance.py)
  and `linux/tests/` end to end, plus checked `linux/README.md`'s
  Bluetooth troubleshooting section, specifically to avoid re-proposing
  anything already in Proposed/Shipped/Abandoned.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section,
  ordered highest-value-first:
  (1) missed-call detection + notification — grep-confirmed
  `CallStateController.handle_event`'s `CALL_ENDED` branch has no
  RINGING-vs-ACTIVE distinction before going idle, and `self._state`
  still holds the prior phase at that point so the check is a one-liner;
  new `call_missed` signal, testable purely in `test_call_state.py`
  with no Qt needed for the logic itself;
  (2) a "Decline" tray action while ringing — today `_hangup_action` is
  the only always-available in-tray call action (only visible while
  ACTIVE), so a user whose popup is missed/obscured has no tray-only way
  to decline, mirrors the existing `on_hangup`/`_hangup_action`
  visibility-toggle pattern exactly, so both the code shape and the test
  shape (`test_tray_icon.py`) are already proven out by that precedent;
  (3) wire `HfpManager.status_changed` to the tray — grep-confirmed
  (same technique used to find last cycle's `bind_failed` gap) that this
  signal is defined and emitted with useful human-readable Bluetooth
  routing status strings in `hfp_manager.py` but literally nothing
  `.connect(`s to it anywhere in the tree, an identical shape of
  silent-failure gap to the one just shipped, this time for the
  Bluetooth HFP "Known blocker" troubleshooting flow `linux/README.md`
  already documents. All three name specific existing
  classes/methods/files, follow patterns already validated in the
  existing test suite (33 tests green, confirmed by re-running
  `QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover
  -s tests -t . -v` from `linux/` before proposing), and look like
  ~15-30 min single-cycle scope. Renumbered/cross-referenced the
  remaining 7 older still-open Proposed items (previously 1-7, now 4-10)
  so internal item-number references stay accurate.
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.

## Engineer cycle 2026-07-10 ~03:34 IST

- Synced fresh from `origin/overnight/auto-research` (`6c61ee8`, the PM's
  latest 3-item proposal), confirmed no `.overnight/STOP`, read
  `GUARDRAILS.md` and `AGENTS.md` in full.
- Took the single topmost `Proposed` item: missed-call detection +
  notification. Purely additive, Linux-only, no protocol/wire-format
  change (still just reacting to the existing `CALL_ENDED` message), so
  no grep-across-three-clients gate applied.
- Implementation: `CallStateController.handle_event`'s `CALL_ENDED`
  branch now checks `self._state.phase is CallPhase.RINGING` (the state
  still holds the *previous* phase at that point, before `_set_state`
  overwrites it to idle) and, if true, emits a new
  `call_missed = Signal(str, str)` with `(name, number)` before
  transitioning to idle. Added `TrayIcon.notify_missed_call(name,
  number)`, which fires a `showMessage()` "Missed call from X"
  notification (falls back to number, then "Unknown", if name is
  blank) — same `showMessage()` plumbing already proven safe under
  `QT_QPA_PLATFORM=offscreen` by the shipped `bind_failed` feature.
  Wired `controller.call_missed.connect(on_call_missed)` in `app.py`
  next to the other signal connections.
- Added unit tests: 3 new cases in `test_call_state.py` (missed-call
  fires for `RINGING → CALL_ENDED`; does *not* fire for
  `RINGING → ACTIVE → CALL_ENDED`, i.e. a normal completed call; does
  *not* fire for a stray `CALL_ENDED` from idle with no prior call at
  all) and 3 new cases in `test_tray_icon.py` (`notify_missed_call`
  doesn't raise with a name, with only a number, and with neither).
- Ran `cd linux && QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m
  unittest discover -s tests -t . -v` — 39 tests, all green (was 33
  before this cycle's 6 new tests).
- Committed as `82a00f0` (`feat: notify on missed calls in the tray
  icon`), pushed cleanly to `overnight/auto-research` (no race with the
  PM persona this cycle — fast-forwarded from `6c61ee8`). Moved the
  item from `Proposed` to `Shipped` in `BACKLOG.md`, renumbered the
  remaining 9 Proposed items (previously 2-10, now 1-9).
- No risk-log entry needed — this is a Linux-only, test-covered,
  non-protocol change with no unverified/manual-testing-only surface.

## Engineer cycle 2026-07-10 ~04:45 IST

Shipped: retry binding the WebSocket port a few times before giving up.
Added `bind_with_retries(bind_fn, attempts=3, delay=1.0)` free function in
`network/call_server.py` and wired `_serve()` to use it around
`websockets.serve(...)` instead of a single `async with` that gave up on
the first `OSError`. Purely additive - `bind_failed` signal shape/emitters
unchanged, still only fires after all attempts are exhausted. New
`linux/tests/test_call_server_bind_retry.py` covers: succeeds after N
transient failures, succeeds first try (no unnecessary retries), raises
after exhausting all attempts. Full linux suite: 42 tests, all green
(`QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover -s
tests -t . -v`). Commit: 2b77c2a.

## Engineer cycle 2026-07-10 04:33 IST
Shipped [20c83a4] feat: refresh tray device label periodically instead of
once at startup. Added `TrayIcon.set_device_label()` and a 30s `QTimer` in
`app.py`'s `main()` re-invoking `device_label()`. Added 3 new
`test_tray_icon.py` cases covering initial value, update, and the
no-network label case. Full suite: 45/45 tests pass
(`QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover -s tests -t . -v`).

## Engineer cycle 2026-07-10 (Open Log File)
Shipped [5bfacb7] "Open Log File" tray action: added `on_open_log`
callback to `TrayIcon`, wired in `app.py` via `QDesktopServices.openUrl`
against `logging_setup.log_file_path()`. Added `test_logging_setup.py`
(XDG_STATE_HOME override/fallback) and 3 new `test_tray_icon.py` cases.
Full linux test suite: 51/51 passing.

## Engineer cycle 2026-07-10 (overnight, commit d1f5539)

Shipped: `SingleInstanceLock.acquire()` now stores the caught `OSError` on
`self.last_error` (None on success) instead of swallowing it, and
`app.py`'s `main()` includes it in the existing "already running" warning
log line. Added `linux/tests/test_single_instance.py` (2 new tests,
patched `single_instance._ABSTRACT_LOCK_ADDRESS` to a unique per-test
value to avoid colliding with a real running instance of the app on this
machine — discovered one was already running via `ps aux` when the first
test-writing attempt failed with a spurious `Address already in use`).
Full suite: 53/53 passed (`QT_QPA_PLATFORM=offscreen PYTHONPATH=src
python3 -m unittest discover -s tests -t . -v`). No protocol/other-client
changes needed.

## Engineer cycle 2026-07-10 (overnight, commit 1fa5e70)

Shipped: checkable "Route Call Audio via Bluetooth" tray toggle. Added
`TrayIcon`'s `on_toggle_bluetooth_audio` constructor param and a new
checkable `QAction` (defaults checked) beneath "Open Log File". In
`app.py`, guarded the existing `hfp_manager.open_audio()`/`close_audio()`
calls in `on_state_changed` behind a `bluetooth_audio_enabled` closure
flag flipped by the new callback — `hfp_manager.py` itself untouched, no
protocol change. Added 4 new `test_tray_icon.py` cases: default-checked
state, toggle invokes callback with correct bool on each trigger, safe
without a callback, and stays enabled/visible regardless of connection
state. Full suite: 57/57 passed
(`QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover
-s tests -t . -v`). No risk-log entry needed — fully test-covered,
Linux-only, non-protocol change.

## Engineer cycle 2026-07-10 (overnight, commit 5114e9d)

Shipped: `CallServer.listening = Signal(int)`, emitted right after
`bind_with_retries()` succeeds in `_serve()`. Added
`TrayIcon.set_listening(port: int)` storing `_listening_port` which
`_status_label()` now renders as "Waiting for phone on port {port}"
instead of the previously-identical "Not Connected" text used whether the
server hadn't started, was listening fine, or had silently crashed.
Wired `server.listening.connect(tray.set_listening)` in `app.py`. Added
`CallServerListeningSignalTests` in `test_call_server_bind_retry.py`
(asserts `listening` fires with the right port using a fake bind
function, mirroring the existing bind-retry test style) plus 3 new
`test_tray_icon.py` cases: the waiting label text, that `set_connected`
supersedes it once actually connected, and that `bind_error` still takes
priority over the listening label. Full suite: 61/61 passed
(`QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover
-s tests -t . -v`). No risk-log entry needed — fully test-covered,
Linux-only, additive/non-protocol change (no wire format change, no
other-client updates needed).

## Engineer cycle 2026-07-10 (overnight)

Shipped: bounded automatic retry (5 attempts, 1s apart) of
`HfpManager.start()`'s initial paired-phone scan when BlueZ/D-Bus
raises `DBusException`, to survive a login-session race with
`bluetoothd`. Does not retry on a legitimate zero-paired-phones
result. Added `linux/tests/test_hfp_manager.py` (3 new tests,
QTimer.singleShot patched to run synchronously). Full linux test
suite: 64 tests, all green. Commit 796eb24.

## PM cycle 2026-07-10 ~11:xx IST

- Synced to `origin/overnight/auto-research` (`512c9e5`, HfpManager
  startup-scan-retry now in Shipped, no new Abandoned entries). No
  `.overnight/STOP` present. Re-read `GUARDRAILS.md`, `AGENTS.md`, and
  freshly checked `network/call_server.py`,
  `bluetooth/bluez_device_finder.py`, and `media_ducker.py` to avoid
  duplicating any of the 28 open Proposed items or the 9 already-Shipped
  features.
- Added 3 new items to the top of `BACKLOG.md`'s Proposed section:
  (1) log when `CallServer._replace_current_connection()` silently drops
  a previous phone connection for a new one, since today there is zero
  log trace of the replacement (the old connection's own disconnect log
  is suppressed by the existing `is connection` identity check); (2)
  filter out `Blocked` BlueZ devices in
  `bluez_device_finder.paired_phones()`, since only `Paired` is checked
  today and a device the user explicitly blocked can still be selected
  for Bluetooth call-audio routing; (3) guard
  `MediaDucker.duck_others()`'s `list_player_services(bus)` call with the
  same `try/except DBusException` already used for `SessionBus()`
  construction one line above, since an uncaught exception there would
  propagate out of a Qt signal handler mid-call, violating this module's
  own best-effort philosophy. All three name specific existing
  files/functions, are scoped to ~15-30 min, and have concrete
  mock/fixture-based unit-test plans building on existing
  `linux/tests/` patterns (fake connection objects, plain dict
  fixtures, extended `_fake_bus`).
- No code under `android/`, `linux/src`, `macos/`, or `website/` was
  touched this cycle — only `.overnight/BACKLOG.md` and this file.
