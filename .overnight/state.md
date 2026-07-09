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
