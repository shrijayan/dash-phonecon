# Overnight Auto-Research — State Log

Append-only running log. Newest entries at the bottom. Each persona cycle
appends a short entry here regardless of outcome, so the next cycle (and
the morning summary) has full visibility without re-deriving it from git
log alone.

## Session start

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
