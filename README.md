# dash-phonecon

Receive and control Android phone calls from your Mac. When your phone rings, a popup appears on your Mac with the caller's name and number. You can answer, decline, or hang up from the Mac. Call audio routing through Mac speakers/mic (Phase 4) is blocked by a macOS 26 API regression — see details below.

---

## What Works (Phases 1–3 — Fully Functional)

| Feature | Status |
|---|---|
| Incoming call popup on Mac with caller name + number | ✅ |
| Answer call from Mac | ✅ |
| Reject incoming call from Mac | ✅ |
| Hang up active call from Mac | ✅ |
| Active call timer in Mac menu bar | ✅ |
| WebSocket auto-reconnect with exponential backoff | ✅ |
| Auto-start Android service on phone reboot | ✅ |
| Connection status in Mac menu bar (grey/green) | ✅ |

## What Does NOT Work

| Feature | Status | Reason |
|---|---|---|
| Call audio through Mac speakers/mic (HFP) | ❌ Blocked | macOS 26 removed the IOBluetooth framework binary — no public API exists for third-party HFP |

---

## Architecture

```
Android Phone (CZ1)                    MacBook (CZ2)
┌──────────────────────┐  WiFi/LAN     ┌─────────────────────┐
│  Foreground Service  │◄─────────────►│  Menu Bar App       │
│  (Kotlin)            │  WebSocket    │  (SwiftUI)          │
│                      │  port 8765    │                     │
│  Phone state         │  CALL_RINGING │  Popup: name+number │
│  listener            │──────────────►│  Answer / Decline   │
│  Contact lookup      │  CALL_ACTIVE  │  Hang up            │
│                      │──────────────►│  Menu bar icon      │
│                      │  CALL_ENDED   │  Active call timer  │
│                      │──────────────►│                     │
│                      │◄──────────────│                     │
│                      │  ANSWER/      │                     │
│                      │  REJECT/      │                     │
│                      │  HANGUP       │                     │
└──────────────────────┘               └─────────────────────┘
           │                                      │
           └──── Bluetooth (paired, ACL only) ────┘
                  HFP audio: BLOCKED (see below)
```

**Protocol:** JSON over WebSocket. Both sides share identical message type constants.

---

## Build & Run

### Prerequisites
- Java 17, ADB, Android SDK (build-tools + platform API 31)
- Swift 6, Xcode Command Line Tools (macOS 26)

### Android
```bash
cd android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Mac
```bash
cd macos
./build.sh
open build/DashPhone.app
```

### First-time setup
1. Make sure both devices are on the same local network (or connected via Tailscale)
2. Open the Android app → enter your Mac's local IP address → tap Start
3. The Mac menu bar icon turns green when connected

---

## Project Structure

```
dash-phonecon/
├── android/
│   └── app/src/main/java/com/dash/phonecon/
│       ├── CallService.kt          # Foreground service — owns WS client, handles call events
│       ├── PhoneStateReceiver.kt   # Detects RINGING / ACTIVE / IDLE states
│       ├── PhoneWebSocketClient.kt # OkHttp WebSocket, exponential backoff (2→60s), 30s ping
│       ├── ContactHelper.kt        # Phone number → contact name lookup
│       ├── BootReceiver.kt         # Auto-starts CallService on reboot
│       └── MainActivity.kt         # UI: enter Mac IP, start/stop service, status display
├── macos/
│   └── DashPhone/
│       ├── DashPhoneApp.swift           # App entry, AppDelegate wires all components
│       ├── Network/CallServer.swift     # NWListener WebSocket server on port 8765
│       ├── Models/CallStateViewModel.swift  # Call state machine (idle/ringing/active)
│       ├── Views/CallPopupWindow.swift  # Floating NSPanel (non-activating, top-right)
│       ├── Views/CallPopupView.swift    # SwiftUI incoming call card
│       ├── Views/MenuBarView.swift      # Menu bar icon + dropdown
│       └── Bluetooth/HFPManager.swift  # HFP audio manager (Phase 4 — blocked, see below)
├── protocol/
│   └── messages.md                 # JSON message spec (source of truth)
├── agentlog.md                     # Chronological change log for agents continuing this work
└── README.md                       # This file
```

---

## Phase 4: Bluetooth HFP Audio — Investigation & Blocker

### Goal
Route call audio through Mac speakers and microphone, the same way a car kit or AirPods work. The Mac would act as a Hands-Free Unit (HFP HF role), the Android phone as the Audio Gateway (AG).

### What HFP requires
1. Mac advertises an **HFP Handsfree (HF)** SDP service record
2. Android detects the HF service → shows "Phone calls" toggle in Bluetooth settings
3. User enables "Phone calls" → Android connects its AG profile to Mac's HF
4. SCO audio channel opens → call audio flows bidirectionally
5. Mac's CoreAudio switches default input/output to the phone's Bluetooth SCO device

### Root cause: macOS 26 removed IOBluetooth

**`IOBluetooth.framework/Versions/A/IOBluetooth` binary is missing** in macOS 26 stable (25F71). Apple intentionally removed it. The framework directory exists (for header compatibility) but the binary does not:

```
/System/Library/Frameworks/IOBluetooth.framework/Versions/A/
  IOBluetooth   ← MISSING (this is the binary)
  Headers/      ← present
  Resources/    ← present
```

`IOBluetoothHandsFreeDevice` class still exists in the **dyld shared cache** (so the app compiles and runs), but `connect()` fires with no callback because the underlying implementation is gone from the developer framework path.

### New private frameworks (macOS 26)
Apple moved classic Bluetooth to private frameworks:
- `BluetoothManager.framework` — new Bluetooth manager (private)
- `BluetoothAudio.framework` — Bluetooth audio routing (private)
- `BTAudioRoutingRequest` / `BTAudioSession` — new audio routing classes

**All of these require Apple system entitlements.** Tested from within the signed DashPhone.app:
- `BluetoothManager.sharedInstance.pairedDevices` → 0 (needs higher privileges than `com.apple.security.device.bluetooth`)
- `BTAudioRoutingRequest` class → not available in app context
- `BTAudioRoutingRequest.isSupported` → false

### Android side findings (ADB)
- Mac (CZ2) advertises `Handsfree_AG` in SDP — the **wrong role** (AG instead of HF)
- Mac never advertises `Handsfree` (HFP HF role) because `IOBluetoothHandsFreeDevice` init no longer registers the SDP record
- Android's "Phone calls" toggle for CZ2 is therefore **not visible** — Android only shows it for devices that advertise HFP HF
- Android's `HEADSET` connection policy for CZ2 = `-1` (UNKNOWN, not ALLOWED)

### System-level confirmation
`system_profiler SPBluetoothDataType` shows the phone (CZ1) connected only with:
```
Services: 0x900000 < GATT ACL >
```
No HFP, no A2DP — the macOS 26 system Bluetooth daemon also does not establish audio profiles with Android.

### What was tried
| Approach | Result |
|---|---|
| `IOBluetoothHandsFreeDevice.connect()` | Fires but no callback — framework binary missing |
| Objective-C test confirming the above | Same result in plain .m file |
| Check IOBluetooth framework symlink | Broken: `Versions/A/IOBluetooth` does not exist |
| `IOBluetoothDevice.performSDPQuery` | Times out on macOS 26 |
| Force HFP from Android via `BluetoothHeadset.connect()` | Requires `BLUETOOTH_PRIVILEGED` (system permission, cannot be granted) |
| `AudioManager.startBluetoothSco()` on Android | No effect — HFP not established |
| Load `BluetoothManager.framework` via dlopen | Loads, but `pairedDevices` = 0 (system entitlement required) |
| `BTAudioRoutingRequest.isSupported` | False / class not available in app context |
| Navigating Android Bluetooth settings via ADB | Settings deep-link to device detail page did not work reliably |

### Current HFPManager.swift state
The code is clean and ready. It:
1. Finds the paired phone via `IOBluetoothDevice.pairedDevices()` (still works)
2. Saves current CoreAudio input/output devices
3. On `CALL_ACTIVE`: starts a 20-attempt retry loop (1s interval) scanning CoreAudio for the phone's device name
4. If the phone ever appears in CoreAudio, it switches system audio to it
5. On `CALL_ENDED`: restores original audio devices

**When Apple ships a public API replacement for IOBluetooth HFP, no code changes will be needed on the Mac side.** The CoreAudio retry loop handles the timing automatically.

### Unblocking path
Apple must provide a public API for HFP audio in macOS 26. File feedback:
- **Feedback Assistant**: [feedbackassistant.apple.com](https://feedbackassistant.apple.com)
- Title: "IOBluetooth.framework binary removed in macOS 26 — no public API replacement for HFP"
- Include: the broken symlink finding, `BTAudioRoutingRequest.isSupported = false`, the use case (third-party HFP for non-iPhone devices)

---

## Devices Tested
- **Android**: Samsung Galaxy A31 (SM-A315F), Android 12 (API 31)
- **Mac**: macOS 26.5 (25F71), Darwin 25.5.0

## Dependencies
- **Android**: OkHttp (WebSocket client), AndroidX LocalBroadcastManager
- **Mac**: Network.framework (NWListener WebSocket server), IOBluetooth (device discovery only), CoreAudio (device switching — ready for when HFP works)
- No external Mac dependencies — pure Swift, builds with `swift build`
