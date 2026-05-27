# Agent Log — dash-phonecon

## 2026-05-27 — Project initialized
Plan approved. Building Android-to-Mac call continuity system (local-only, Phase 1).
Architecture: Android Kotlin foreground service + Mac SwiftUI menu bar app, connected via WebSocket over local WiFi. Bluetooth HFP for call audio.

## 2026-05-27 — Parallel development started
Spinning two agents simultaneously:
- Agent A: Android Kotlin app (Phases 1–3: network, call detection, call control)
- Agent B: Mac SwiftUI menu bar app (Phases 1–3: network server, popup UI, call control)

Protocol spec lives in protocol/messages.md (source of truth for both apps).
