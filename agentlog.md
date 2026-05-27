# Agent Log — dash-phonecon

## 2026-05-27 — Project initialized
Plan approved. Building Android-to-Mac call continuity system (local-only, Phase 1).
Architecture: Android Kotlin foreground service + Mac SwiftUI menu bar app, connected via WebSocket over local WiFi. Bluetooth HFP for call audio.

## 2026-05-27 — Parallel development started
Spinning two agents simultaneously:
- Agent A: Android Kotlin app (Phases 1–3: network, call detection, call control)
- Agent B: Mac SwiftUI menu bar app (Phases 1–3: network server, popup UI, call control)

Protocol spec lives in protocol/messages.md (source of truth for both apps).

## 2026-05-27 — Android app Phases 1–3 complete
Created complete Android project at android/ with 17 files:
- settings.gradle, build.gradle (root + app), gradle/wrapper files — buildable with ./gradlew assembleDebug
- MessageType.kt — all protocol constants (no magic strings)
- PhoneWebSocketClient.kt — OkHttp WebSocket, exponential backoff (2→60s), 30s PING, resetPingTimer on any received message
- ContactHelper.kt — ContentResolver PhoneLookup utility
- PhoneStateReceiver.kt — TelephonyManager state change receiver, delegates to CallEventListener
- CallService.kt — foreground service (phoneCall type), wires WS client + phone receiver, handles ANSWER/REJECT/HANGUP via TelecomManager (reflection fallback for API<28), broadcasts LocalBroadcastManager status
- BootReceiver.kt — auto-starts CallService on boot if mac_ip is saved
- MainActivity.kt — IP input (persisted to SharedPreferences), Start/Stop toggle, live status updates via LocalBroadcast
- AndroidManifest.xml, activity_main.xml, strings.xml

Next: Mac SwiftUI agent completes its side (WebSocket server on port 8765, popup on CALL_RINGING, ANSWER/REJECT commands).

## 2026-05-27 — macOS app (Phases 1–3) completed

Created all Swift source files under `macos/DashPhone/`:

- `Models/MessageType.swift` — enum with all protocol message type raw string values
- `Models/CallStateViewModel.swift` — @MainActor ObservableObject; owns CallState enum (.idle/.ringing/.active), handles incoming events, drives popup show/close
- `Network/CallServer.swift` — NWListener on TCP 8765; newline-delimited JSON framing; publishes isConnected; dispatches parsed events to viewModel via Task @MainActor
- `Views/CallPopupWindow.swift` — @MainActor NSPanel wrapper; positions top-right near menu bar; non-activating floating panel
- `Views/CallPopupView.swift` — SwiftUI incoming call card with Answer (green, Return key) and Decline (red, Escape key) buttons
- `Views/ActiveCallTimerView.swift` — TimelineView(.periodic) MM:SS elapsed timer
- `Views/MenuBarView.swift` — menu bar dropdown: connection status dot, active call timer + Hang Up, Quit
- `DashPhoneApp.swift` — @main SwiftUI App; AppDelegate owns single CallServer + CallStateViewModel instances; MenuBarIconView reacts to state changes; MenuBarExtra for macOS 13+
- `Info.plist` — LSUIElement=true (no Dock icon), macOS 13 min
- `DashPhone.entitlements` — app-sandbox + network server + network client
- `macos/README-xcode-setup.md` — step-by-step Xcode project creation guide

Key design decisions:
- AppDelegate holds the single source-of-truth server/viewModel pair to avoid duplicate instances that @main + @StateObject would create
- @MainActor on CallStateViewModel and CallPopupWindow ensures all AppKit/UI operations run on main thread
- CallServer.start() is @MainActor; processBuffer dispatches to main actor via Task for thread safety
- NWListener/NWConnection run on .main queue directly; no extra thread management needed

Note: Android side uses WebSocket (OkHttp); Mac side uses raw TCP + newline-delimited JSON per the updated spec. Both sides use the same MessageType string constants.

## 2026-05-27 — Mac side upgraded to WebSocket (NWProtocolWebSocket)
Replaced raw TCP NWListener with NWProtocolWebSocket (Apple Network.framework, built-in macOS 13+).
- No external dependencies (Starscream not needed)
- HTTP upgrade handshake handled automatically by the framework
- autoReplyPing = true handles WebSocket-level ping/pong natively
- receiveMessage() replaces manual newline buffer — WebSocket framing handles message boundaries
- send() uses NWProtocolWebSocket.Metadata(opcode: .text) for proper WS text frames
- README-xcode-setup.md updated: verification now uses websocat (brew install websocat) instead of nc
Both Android (OkHttp WebSocket) and Mac (NWProtocolWebSocket) now speak the same protocol.
