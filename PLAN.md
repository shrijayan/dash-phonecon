# dash-phonecon — Build Plan

## What This Is
Android-to-Mac call continuity. When Android phone rings, Mac shows a native menu bar popup with caller name + number. User can answer, decline, or hang up from the Mac. Audio routes via Bluetooth HFP.

## Architecture

```
Android Phone                         MacBook
┌──────────────────┐    WiFi          ┌─────────────────────┐
│  Foreground      │◄────────────────►│  Menu Bar App       │
│  Service (Kotlin)│  WebSocket:8765  │  (SwiftUI)          │
│                  │                  │                     │
│  PhoneState      │  → CALL_RINGING  │  Popup: name+number │
│  Listener        │  → CALL_ACTIVE   │  Answer / Decline   │
│  Contact lookup  │  → CALL_ENDED    │  Hang up            │
│                  │  ← ANSWER        │  Menu bar icon      │
│                  │  ← REJECT        │  (idle/ringing/     │
│                  │  ← HANGUP        │   active)           │
└──────────────────┘                  └─────────────────────┘
         │                                       │
         └───────── Bluetooth HFP ───────────────┘
                   Full duplex audio (Phases 4+)
```

## Message Protocol (JSON over WebSocket)

Phone → Mac (events):
- `{ "type": "CALL_RINGING", "number": "+15551234567", "name": "John Doe" }`
- `{ "type": "CALL_ACTIVE" }`
- `{ "type": "CALL_ENDED" }`
- `{ "type": "PING" }`

Mac → Phone (commands):
- `{ "type": "ANSWER" }`
- `{ "type": "REJECT" }`
- `{ "type": "HANGUP" }`
- `{ "type": "PONG" }`

## Project Structure

```
dash-phonecon/
├── android/                          # Kotlin Android app
├── macos/                            # Swift/SwiftUI Mac app
├── protocol/messages.md              # Protocol spec (source of truth)
├── PLAN.md                           # This file
└── agentlog.md                       # Agent progress log
```

## Phases

### Phase 1 — Network Foundation
- Mac: NWListener on port 8765
- Android: OkHttp WebSocket client, connects to Mac IP from settings
- PING/PONG every 30s, Android auto-reconnects with exponential backoff

### Phase 2 — Call Detection & Popup
- Android: PhoneStateListener detects RINGING, ContactHelper looks up name
- Sends CALL_RINGING to Mac
- Mac: SwiftUI NSPanel popup with name + number + Answer/Decline buttons

### Phase 3 — Call Control (Mac → Android)
- Answer/Reject/Hangup from Mac sends command to Android
- Android executes via TelecomManager
- Mac shows active call state with elapsed timer

### Phase 4 — Bluetooth Audio (later)
- IOBluetooth HFP audio routing on Mac
- CoreAudio device switching on call active/ended

### Phase 5 — Polish (later)
- mDNS auto-discovery (no manual IP entry)
- Boot persistence on Android
- Mac launch at login
