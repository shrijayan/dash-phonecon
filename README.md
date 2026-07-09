# dash-phonecon

Receive and control Android phone calls from your computer. When your phone rings, a popup appears with the caller's name and number. You can answer, decline, or hang up without touching your phone. Two desktop clients exist, both speaking the exact same WiFi protocol to the same Android app:

- **macOS** (`macos/`) — menu bar app. Call audio routing through Mac speakers/mic (Phase 4) is blocked by a macOS 26 API regression — see details below.
- **Ubuntu** (`linux/`) — system tray app, installable as a `.deb`. Same popup/answer/decline/hang-up features, plus a best-effort attempt at call audio routing over Bluetooth (Linux's PipeWire is not blocked the way macOS 26 is) — see `linux/README.md`.

The Android app needs **no changes** to work with either — just type whichever computer's IP address into it.

---

## What Works (Phases 1–3 — Fully Functional, both platforms)

| Feature | Status |
|---|---|
| Incoming call popup with caller name + number | ✅ macOS + Ubuntu |
| Answer call from computer | ✅ macOS + Ubuntu |
| Reject incoming call from computer | ✅ macOS + Ubuntu |
| Hang up active call from computer | ✅ macOS + Ubuntu |
| Active call timer in menu bar / tray | ✅ macOS + Ubuntu |
| WebSocket auto-reconnect with exponential backoff | ✅ (Android side, shared) |
| Auto-start Android service on phone reboot | ✅ |
| Connection status indicator | ✅ macOS + Ubuntu |

## Call Audio Routing (Phase 4) — platform-dependent

| Platform | Status | Reason |
|---|---|---|
| macOS | ❌ Blocked | macOS 26 removed the IOBluetooth framework binary — no public API exists for third-party HFP |
| Ubuntu | ⚠️ Blocked (for now) | Confirmed on real hardware: pairing + Android's connection policy both work correctly (further than macOS gets), but PipeWire/BlueZ fails to complete the actual Hands-Free transport connection with a reproducible error. Not a hard OS-level wall like macOS - looks like a fixable bug/version issue. See `linux/README.md`'s "Known blocker" section for the exact error and next steps. |

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

The Ubuntu client (`linux/`) uses the identical architecture and wire protocol — just swap "MacBook (CZ2)" above for "Ubuntu PC", and "BLOCKED" for "best-effort" (see `linux/README.md`).

**Protocol:** JSON over WebSocket. All sides share identical message type constants — currently duplicated by hand in `android/.../MessageType.kt`, `macos/DashPhone/Models/MessageType.swift`, and `linux/src/dashphone/protocol/message_type.py`. If you change one, change all three.

---

## Build & Run

### Prerequisites
- Java 17, ADB, Android SDK (build-tools + platform API 31)
- Swift 6, Xcode Command Line Tools (macOS 26) — for the macOS client
- Python 3.10+ (Ubuntu 24.04+) — for the Ubuntu client

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

### Ubuntu
```bash
cd linux
./build-deb.sh
sudo apt install ./dist/dash-phonecon_*_all.deb
```
See `linux/README.md` for running from source without packaging, and for Bluetooth audio setup/troubleshooting.

### First-time setup
1. Make sure both devices are on the same local network (or connected via Tailscale)
2. Open the Android app → enter your computer's local IP address → tap Start
3. The menu bar (Mac) or tray (Ubuntu) icon turns green when connected

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
├── linux/
│   ├── build-deb.sh                     # assembles the installable .deb package
│   ├── packaging/                       # Debian control file, postinst/postrm, .desktop entry
│   └── src/dashphone/
│       ├── app.py                       # composition root, wires everything together
│       ├── protocol/message_type.py     # shared message-type vocabulary (source of truth, Ubuntu side)
│       ├── state/                       # CallState + CallStateController (pure logic, no Qt/network)
│       ├── network/call_server.py       # asyncio WebSocket server on port 8765
│       ├── bluetooth/                   # best-effort Bluetooth Hands-Free audio routing (Phase 4)
│       └── ui/                          # tray icon, incoming-call popup
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

## FAQ: "But AirDroid / KDE Connect can do call audio — why can't this?"

**Short answer: AirDroid works on specific phones only, because of OEM deals — not because they found a trick we missed.**

### The Android permission wall

To capture both sides of a phone call (your voice + the caller's voice) as audio data, an app needs one of these `AudioRecord` sources:

| Source | What it captures | Permission required |
|---|---|---|
| `VOICE_CALL` | Both sides | `CAPTURE_AUDIO_OUTPUT` — system/OEM only |
| `VOICE_DOWNLINK` | Caller's voice only | `CAPTURE_AUDIO_OUTPUT` — system/OEM only |
| `VOICE_COMMUNICATION` | Your mic only | `RECORD_AUDIO` — any app |

`CAPTURE_AUDIO_OUTPUT` **cannot be granted by the user**. It is only available to APKs pre-installed on the device or signed with the OEM's platform key. No sideloaded app can get it on stock Android.

### How AirDroid does it

AirDroid has **OEM partnerships** (primarily Samsung). On supported devices, their APK ships pre-installed or is signed with elevated privileges that unlock `VOICE_CALL` audio capture. That is why their own documentation says *"call handling support depends on phone"* — on a stock Android device with a user-installed APK, they hit the same wall.

### What about a SIP bridge?

A SIP bridge routes audio over WiFi instead of Bluetooth, which bypasses the macOS 26 IOBluetooth blocker. But it does not bypass the Android audio capture restriction — you still need `CAPTURE_AUDIO_OUTPUT` to capture the caller's voice. Both approaches hit the same Android permission wall.

### What can be done today (without OEM access)

The only option on a stock device is the **speakerphone workaround**: force the call to speakerphone on `CALL_ACTIVE`, then use `AudioRecord` with `VOICE_COMMUNICATION` (mic source). The mic acoustically picks up both voices from the speaker. It works on any phone but the audio quality is degraded.

### Unblocking path

Either Google adds a user-grantable permission for call audio capture, or the device is rooted. Neither is in scope for this project.

### Why doesn't this wall also block Ubuntu's Bluetooth approach?

It's a different mechanism entirely. The wall above applies to an **app** trying to grab call audio in software via Android's `AudioRecord` API. Bluetooth HFP is not that — it's native OS/Bluetooth-stack behaviour, the same path a real Bluetooth headset or car kit uses, and it requires no special Android app permission at all. That's why the Ubuntu client's approach (`linux/bluetooth/`) is a legitimately different, unblocked path rather than a workaround for this same wall — see `linux/README.md` for how it depends instead on your phone's Bluetooth stack allowing the "Phone calls" HFP toggle.

---

## Devices Tested
- **Android**: Samsung Galaxy A31 (SM-A315F), Android 12 (API 31)
- **Mac**: macOS 26.5 (25F71), Darwin 25.5.0
- **Ubuntu**: 26.04 LTS "Resolute Raccoon", PipeWire 1.6.2, BlueZ 5.85 — WiFi call control (Phases 1–3) verified end-to-end; Bluetooth audio routing (Phase 4) implemented and unit-tested, but not yet confirmed with a real paired phone (needs `linux/README.md`'s "Phone calls" toggle step) — see `agentlog.md` for the current state.

## Dependencies
- **Android**: OkHttp (WebSocket client), AndroidX LocalBroadcastManager
- **Mac**: Network.framework (NWListener WebSocket server), IOBluetooth (device discovery only), CoreAudio (device switching — ready for when HFP works)
- No external Mac dependencies — pure Swift, builds with `swift build`
- **Ubuntu**: PySide6 (Qt widgets/tray icon), `websockets` (asyncio WebSocket server) — both from Ubuntu's own `universe` repo, installed automatically as `.deb` dependencies. Bluetooth audio routing additionally uses `python3-dbus` (talks to BlueZ) and `pactl`/PipeWire (audio device switching), declared as `Recommends:` since the core features work without them.
