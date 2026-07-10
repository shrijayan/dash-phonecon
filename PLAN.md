# dash-phonecon — Build Plan

## What This Is
Android-to-desktop call continuity. When the Android phone rings, the desktop (Mac or Ubuntu) shows a native popup with caller name + number. User can answer, decline, or hang up from the desktop. Audio routes via Bluetooth HFP (blocked on macOS 26, best-effort on Ubuntu - see `README.md`).

## Architecture

```
Android Phone                         Mac or Ubuntu
┌──────────────────┐    WiFi          ┌─────────────────────┐
│  Foreground      │◄────────────────►│  Menu Bar / Tray App│
│  Service (Kotlin)│  WebSocket:8765  │  (SwiftUI / PySide6) │
│                  │                  │                     │
│  PhoneState      │  → CALL_RINGING  │  Popup: name+number │
│  Listener        │  → CALL_ACTIVE   │  Answer / Decline   │
│  Contact lookup  │  → CALL_ENDED    │  Hang up            │
│                  │  ← ANSWER        │  Menu bar/tray icon │
│                  │  ← REJECT        │  (idle/ringing/     │
│                  │  ← HANGUP        │   active)           │
└──────────────────┘                  └─────────────────────┘
         │                                       │
         └───────── Bluetooth HFP ───────────────┘
                   Full duplex audio (Phase 4)
```

The Android app is a single shared client for both desktop platforms -
same protocol, same port, just point it at whichever computer's IP
address you're using.

## Message Protocol (JSON over WebSocket)

Phone → desktop (events):
- `{ "type": "CALL_RINGING", "number": "+15551234567", "name": "John Doe" }`
- `{ "type": "CALL_ACTIVE" }`
- `{ "type": "CALL_ENDED" }`
- `{ "type": "PING" }`

Desktop → phone (commands):
- `{ "type": "ANSWER" }`
- `{ "type": "REJECT" }`
- `{ "type": "HANGUP" }`
- `{ "type": "PONG" }`

This exact vocabulary is duplicated by hand in three places - keep them
in sync when it changes:
- `android/app/src/main/java/com/dash/phonecon/MessageType.kt`
- `macos/DashPhone/Models/MessageType.swift`
- `linux/src/dashphone/protocol/message_type.py`

## Project Structure

```
dash-phonecon/
├── android/                          # Kotlin Android app (shared by both desktop clients)
├── macos/                            # Swift/SwiftUI Mac app
├── linux/                            # Python/PySide6 Ubuntu app (.deb packaged)
├── PLAN.md                           # This file
└── agentlog.md                       # Agent progress log
```

## Phases

### Phase 1 — Network Foundation
- Desktop: WebSocket server on port 8765 (Mac: `NWListener`; Ubuntu: Python `websockets`)
- Android: OkHttp WebSocket client, connects to desktop IP from settings
- PING/PONG every 30s, Android auto-reconnects with exponential backoff
- Status: done (Mac, Ubuntu)

### Phase 2 — Call Detection & Popup
- Android: PhoneStateListener detects RINGING, ContactHelper looks up name
- Sends CALL_RINGING to the desktop
- Desktop: popup with name + number + Answer/Decline buttons (Mac: SwiftUI `NSPanel`; Ubuntu: PySide6 frameless `QWidget`)
- Status: done (Mac, Ubuntu)

### Phase 3 — Call Control (Desktop → Android)
- Answer/Reject/Hangup from the desktop sends a command to Android
- Android executes via TelecomManager
- Desktop shows active call state with elapsed timer
- Status: done (Mac, Ubuntu)

### Phase 4 — Bluetooth Audio
- Mac: IOBluetooth HFP audio routing + CoreAudio device switching on call active/ended
  - Status: **blocked** - macOS 26 removed the IOBluetooth framework binary (see `README.md`)
- Ubuntu: BlueZ (via D-Bus) finds the paired phone, PipeWire/`pactl` switches default sink/source to the phone's Hands-Free connection on call active/ended
  - Status: implemented + unit-tested (`linux/src/dashphone/bluetooth/`), **not yet confirmed against a real paired phone** - depends on the phone's Android/OEM Bluetooth stack allowing the "Phone calls" HFP toggle. See `linux/README.md` for setup + troubleshooting.

### Phase 5 — Polish (later)
- mDNS auto-discovery (no manual IP entry)
- Boot persistence on Android
- Launch at login (Mac: Login Items; Ubuntu: already done via `/etc/xdg/autostart` in the `.deb`)

### Phase 6 — Screen Share
- Ubuntu: tray menu "Screen Share Phone" launches `scrcpy` over `adb connect <phone-ip>:5555`, reusing the same IP the WebSocket call-control connection already uses (`CallServer.phone_ip_address`)
- Requires one-time "Wireless debugging" enable on the phone (see `linux/README.md#screen-share`)
- Not part of the JSON/WebSocket protocol - a separate adb/scrcpy transport, so no protocol.mdx changes needed
- Status: implemented + unit-tested (Ubuntu). Not yet built for macOS/Android (Android is the phone being mirrored, not a mirroring client).
