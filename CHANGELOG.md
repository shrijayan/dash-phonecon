# Changelog

All notable changes to dash-phonecon are documented here, auto-generated from Conventional Commit messages on every release.

## v1.2.0 - 2026-07-10

### Features
- **ci:** auto-generate CHANGELOG.md entries on every release
- merge DIAL into Contacts, remove standalone DIAL feature
- visible call log + real Phone/Contacts UI redesign (dark tabbed window)
- full Contacts CRUD synced with phone's real Contacts, dial-by-contact from Linux tray
- Clear Log File action, filter blocked BT devices, deterministic phone tie-break
- add dial-from-desktop (DIAL protocol message)
- **linux:** stop repeating pactl-not-installed warnings across HFP retry loop
- log when a new phone connection replaces an existing one
- retry HfpManager startup scan on transient BlueZ D-Bus errors
- surface CallServer.listening in the tray status instead of generic "Not Connected"
- add checkable Bluetooth call-audio routing toggle to tray icon
- log the underlying OSError when single-instance lock acquire fails
- add "Open Log File" tray action
- refresh tray device label periodically instead of once at startup
- retry binding the WebSocket port a few times before giving up
- notify on missed calls in the tray icon
- **linux:** surface bind_failed to the tray icon instead of dropping it silently

### Fixes
- **ci:** test-linux job never installed websockets, only PySide6
- relaunch-friendly single instance, dedup contacts, UI polish

### Other
- log call-log request/response for live troubleshooting
- overnight loop cutoff -- stopping autonomous cycles
- update backlog/state after shipping pactl-not-installed HFP fix
- **pm:** propose 3 new backlog items
- move replace-connection logging item to Shipped
- **pm:** propose 3 new backlog items
- move HfpManager startup-scan-retry item to Shipped
- **pm:** propose 3 new backlog items
- update backlog and state log after listening-signal ship
- **pm:** propose 3 new backlog items
- update backlog and state log after Bluetooth toggle ship
- **pm:** propose 3 new backlog items
- move single-instance error logging item to Shipped
- **pm:** propose 3 new backlog items
- update backlog and state after shipping Open Log File action
- **pm:** propose 3 new backlog items
- update backlog and state after shipping tray device-label refresh
- **pm:** propose 3 new backlog items
- update backlog/state after bind-retry ship
- **pm:** propose 3 new backlog items
- simplify notify_missed_call fallback to an or-chain
- move missed-call item to Shipped, log engineer cycle
- **pm:** propose 3 new backlog items
- **overnight:** move bind_failed item to Shipped, log engineer cycle
- **pm:** propose 3 new backlog items
- scaffold overnight auto-research loop (guardrails, backlog, state log)
