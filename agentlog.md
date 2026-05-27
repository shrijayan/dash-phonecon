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

## 2026-05-27 — Phase 4 complete: Bluetooth HFP audio routing added

Integrated `HFPManager.swift` (IOBluetooth) into the Mac app:

- `HFPManager.start()` now auto-connects via `IOBluetoothHandsFreeDevice` immediately after finding the paired phone (class of device major class 0x02)
- `CallStateViewModel` gains `attach(hfpManager:)` — calls `openAudio()` (SCO) on `CALL_ACTIVE` and `closeAudio()` on `CALL_ENDED`
- `AppDelegate` creates `HFPManager`, wires it to `viewModel`, and starts it in `applicationDidFinishLaunching`
- `DashPhone.entitlements`: disabled app-sandbox (`<false/>`), added `com.apple.security.device.bluetooth`
- `Info.plist`: added `NSBluetoothAlwaysUsageDescription` (required for macOS privacy TCC prompt)

Pre-requisite: user must pair Android phone to Mac once via System Settings → Bluetooth before call audio will route.

## 2026-05-27 — Mac side upgraded to WebSocket (NWProtocolWebSocket)
Replaced raw TCP NWListener with NWProtocolWebSocket (Apple Network.framework, built-in macOS 13+).
- No external dependencies (Starscream not needed)
- HTTP upgrade handshake handled automatically by the framework
- autoReplyPing = true handles WebSocket-level ping/pong natively
- receiveMessage() replaces manual newline buffer — WebSocket framing handles message boundaries
- send() uses NWProtocolWebSocket.Metadata(opcode: .text) for proper WS text frames
- README-xcode-setup.md updated: verification now uses websocat (brew install websocat) instead of nc
Both Android (OkHttp WebSocket) and Mac (NWProtocolWebSocket) now speak the same protocol.

## 2026-05-27 — README written, speakerphone revert, project finalized at Phase 3
Reverted AudioManager.isSpeakerphoneOn change (user does not want speakerphone workaround — wants HFP or nothing). Reinstalled clean APK. Wrote README.md with full project status, architecture, blocker analysis, and what-was-tried table.

## 2026-05-27 — Phase 4 BLOCKED: macOS 26 stable removed IOBluetooth, no public replacement
Full investigation confirmed:
- IOBluetooth.framework Versions/A/IOBluetooth binary is MISSING — Apple intentionally removed it in macOS 26 stable (25F71)
- IOBluetoothHandsFreeDevice class exists in dyld shared cache (so the app compiles/runs) but connect() callback never fires
- Mac only advertises Handsfree_AG (AG role) in SDP, not Handsfree (HF role) — so Android cannot show "Phone calls" toggle
- New private frameworks: BluetoothManager.framework, BluetoothAudio.framework, BTAudioRoutingRequest — all locked to Apple system processes (require system entitlements)
- BluetoothManager.sharedInstance sees 0 paired devices (vs IOBluetooth which sees CZ1)
- BTAudioRoutingRequest class not available in app context; isSupported=false even in signed binary
- CZ1 never appears in CoreAudio as an audio device — HFP is never established at any level
Verdict: HFP call audio routing through Mac is impossible for third-party apps on macOS 26. No public API replacement exists. App is complete for Phases 1–3 (call control) and will gain audio when Apple provides a public replacement for IOBluetooth.

## 2026-05-27 — Phase 4 rework: drop IOBluetoothHandsFreeDevice (broken on macOS 26 beta)
Root cause confirmed: IOBluetooth.framework has a broken symlink on Darwin 25.5.0. `IOBluetoothHandsFreeDevice.connect()` fires but the callback never comes — verified in both Swift and plain Objective-C. The entire programmatic HFP initiation from Mac side is a no-op on this OS.
New approach: remove IOBluetoothHandsFreeDevice entirely. Mac only does CoreAudio device switching. Android initiates HFP (once "Phone calls" is enabled in Android BT settings for the Mac device). Mac's system Bluetooth daemon accepts the incoming HFP connection, phone appears as a CoreAudio audio device, and our 20-attempt retry loop switches default I/O to it.
Prerequisite the user must do manually: Settings → Connections → Bluetooth → tap ⚙️ next to CZ2 → enable "Phone calls" toggle. This changes Android's connection policy from HEADSET=-1 (UNKNOWN) to HEADSET=100 (ALLOWED), which causes Android to auto-connect HFP.
Rebuilt Mac app — build clean.

## 2026-05-27 — Fix: caller showing "Unknown" instead of number/name
Root cause: `EXTRA_INCOMING_NUMBER` from `ACTION_PHONE_STATE_CHANGED` requires `READ_CALL_LOG` on Android 9+ in addition to `READ_PHONE_STATE`. Without it the number is null, so contact lookup never runs and "Unknown" is displayed.
Fix: Added `READ_CALL_LOG` permission to AndroidManifest.xml and to the runtime permission request list in MainActivity.kt. After reinstalling the app, Android will prompt for Call Log permission — grant it.
