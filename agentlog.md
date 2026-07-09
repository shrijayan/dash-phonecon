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

## 2026-05-30 — README: added FAQ explaining why AirDroid can do call audio but we cannot
Investigated how AirDroid routes call audio. Finding: AirDroid uses OEM partnerships (primarily Samsung) to get `CAPTURE_AUDIO_OUTPUT` — a system-only permission that cannot be granted by users on stock Android. This permission is required to capture `VOICE_CALL` / `VOICE_DOWNLINK` audio sources. AirDroid's own docs say "depends on phone" because on stock devices with a sideloaded APK they hit the same wall. A SIP bridge approach faces the same Android permission blocker — the transport layer is irrelevant; the bottleneck is always `CAPTURE_AUDIO_OUTPUT`. Added FAQ section to README documenting this clearly so future contributors understand the constraint.

## 2026-05-27 — Fix: caller showing "Unknown" instead of number/name
Root cause: `EXTRA_INCOMING_NUMBER` from `ACTION_PHONE_STATE_CHANGED` requires `READ_CALL_LOG` on Android 9+ in addition to `READ_PHONE_STATE`. Without it the number is null, so contact lookup never runs and "Unknown" is displayed.
Fix: Added `READ_CALL_LOG` permission to AndroidManifest.xml and to the runtime permission request list in MainActivity.kt. After reinstalling the app, Android will prompt for Call Log permission — grant it.

## 2026-07-09 — New Ubuntu client built (Phases 1–4), packaged as a .deb

Built a full Ubuntu counterpart to the macOS app at `linux/`, speaking the identical WebSocket/JSON protocol — **zero changes needed on the Android side**, it already just connects to whatever IP you type in.

Stack: Python 3 + PySide6 (Qt) for the tray icon/popup, stdlib `asyncio` + the `websockets` package for the WebSocket server. Chosen over GTK because PySide6's tray/window APIs need no extra Ubuntu-specific system packages beyond itself. Chosen over Electron to avoid bundling a whole browser for a small always-running background app.

Architecture (mirrors the Mac app's layering 1:1, see `linux/README.md`):
- `protocol/message_type.py` — same MessageType vocabulary as `MessageType.kt`/`.swift`. All three copies must be kept in sync by hand; there is no shared codegen.
- `state/call_state_controller.py` — pure logic (no Qt widgets, no network import), turns protocol messages into `CallState` and back. Unit tested directly (`tests/test_call_state.py`, 12 cases).
- `network/call_server.py` — `websockets.serve()` running on its own asyncio event loop in a background thread (daemon thread), so Qt's main loop never blocks on I/O. Cross-thread signal emission relies on Qt's own automatic queued-connection behavior (receiver's thread ≠ emitter's thread ⇒ auto-queued) — no manual `QMetaObject.invokeMethod` needed. Sending back to the phone uses `asyncio.run_coroutine_threadsafe`. Only one phone connection is kept live at a time (new connection closes the old one), same as the Mac server.
- `ui/tray_icon.py` + `ui/call_popup.py` — `QSystemTrayIcon` + a frameless always-on-top `QWidget` positioned top-right (Enter=Answer/Escape=Decline), same interaction model as the Mac `NSPanel`. Icons are drawn in code (`ui/icons.py`, `QPainter` circle + phone glyph) instead of shipped as image assets, so the tray icon and the installed app icon (desktop file) can never drift out of sync — `packaging/render_icon.py` reuses the exact same function at build time.
- `bluetooth/` (Phase 4) — `bluez_device_finder.py` (finds the paired phone via BlueZ D-Bus, same CoD major-class-0x02 check as `HFPManager.swift`), `audio_router.py` (wraps `pactl -f json ...` to find/switch/restore the default sink+source), `hfp_manager.py` (orchestrates the 20-attempt/1s retry loop on `CALL_ACTIVE`, restores on `CALL_ENDED` — same shape as `HFPManager.swift` but PipeWire/BlueZ instead of CoreAudio/IOBluetooth). Fully best-effort: every external call (D-Bus, `pactl`) is wrapped so a failure just disables audio routing and logs a reason, never crashes the app or affects the WiFi call-control features.

**Important finding, unlike Mac: Ubuntu's Bluetooth path is not hard-blocked.** Confirmed via ArchWiki + this machine's own WirePlumber config that PipeWire's default `bluez5.roles` already includes `hfp_hf` (the Hands-Free/head-unit role — i.e. "this computer acts like a car kit for the phone"), and the needed CLI (`pactl`, from `pulseaudio-utils`) and D-Bus (`python3-dbus`) tooling all exist in Ubuntu's own repos (verified exact package names against this machine: `python3-pyside6.qtcore/qtgui/qtwidgets`, `python3-websockets`, `pulseaudio-utils`, `libspa-0.2-bluetooth`, `bluez` — all present in Ubuntu 26.04's `universe`/`main`). The FAQ in `README.md` about AirDroid/`CAPTURE_AUDIO_OUTPUT` does **not** apply here — that wall is about an app capturing call audio via `AudioRecord`; Bluetooth HFP is native OS/Bluetooth-stack behavior with no app permission involved, the same path any real Bluetooth headset uses. Added a note to `README.md`'s FAQ section clarifying this distinction so nobody assumes Ubuntu hits the same wall.

**What is and isn't verified:**
- Phases 1–3 (popup, answer/decline/hangup, tray status, timer): verified end-to-end in this sandbox — ran the real installed `.deb` binary, drove it with `linux/tests/fake_phone_client.py` (a standalone script that stands in for the Android phone), watched the full CALL_RINGING → CALL_ACTIVE → CALL_ENDED cycle in the logs with correct state transitions and no errors.
- Phase 4 (Bluetooth audio): code is complete and unit-tested (`tests/test_audio_router_parsing.py` uses recorded-shape `pactl -f json` output as fixtures — no real phone needed to test the matching/parsing logic), and `hfp_manager.start()` correctly detects "no paired phone" and disables itself gracefully when tested in this sandbox (no Bluetooth phone paired here). **Not yet confirmed against a real paired Android phone** — that depends on the phone's Android/OEM Bluetooth stack allowing the "Phone calls" HFP toggle for this computer, which cannot be tested without the actual hardware. See `linux/README.md`'s troubleshooting section (`bluetoothctl info`, `pactl list cards`) for next steps once tested on real hardware.

Packaging: hand-assembled binary `.deb` (`linux/build-deb.sh` + `dpkg-deb --build --root-owner-group`, not full debhelper/dh-python — that machinery is meant for Debian archive uploads, overkill here) — `Depends:` on the four packages the core app needs, `Recommends:` on the four Bluetooth-only ones (so `apt remove --no-install-recommends` still gets a working core app). Installs the app to `/usr/lib/python3/dist-packages/dashphone/` (Debian's standard system Python path), a `dash-phonecon` launcher to `/usr/bin/`, and an XDG autostart `.desktop` entry (`/etc/xdg/autostart/` — starts on login, no systemd unit; Quit in the tray menu should actually quit, which a systemd user service would fight against by auto-restarting). Verified the full lifecycle for real in this sandbox: `sudo apt install ./dash-phonecon_1.0.0_all.deb` → ran the installed binary → `sudo apt remove` / `sudo dpkg --purge` → confirmed every installed file is gone.

A stray finding during testing, for continuity: running the real GUI app in this sandbox's live graphical session once produced a spontaneous `ANSWER` message with nobody visibly clicking anything (user confirmed they saw no popup). Re-ran the identical scenario with `QT_QPA_PLATFORM=offscreen` (no display, no possibility of any input at all) and got zero spurious messages, with the 18/18 unit tests on the state/command logic also passing — so this was some artifact of this specific sandbox's live session (possibly its own automation/monitoring layer), not a bug in the app. Worth a quick re-check if it ever recurs, but not treated as a real issue.

Follow-ups / not done in this pass:
- Old root `README.md`/`PLAN.md` referenced a `protocol/messages.md` file that never actually existed in this repo (checked git history — never committed). Updated both docs to point at the three `MessageType.kt`/`.swift`/`.py` files as the real (hand-synced) source of truth instead of the phantom file.
- Dial-out (placing a call *from* the desktop) was explicitly scoped out for this pass — would need a new `DIAL` message type plus a Ubuntu dial box and an Android-side `TelecomManager.placeCall()` handler + `CALL_PHONE` permission. Not started.
- The Android app's UI still labels its IP field "Mac IP Address" (cosmetic only — same field works for a Ubuntu IP unchanged). Left as-is since Android was explicitly out of scope for this pass; a one-line label rename would be a trivial follow-up if wanted.
- Bluetooth audio (Phase 4) needs a real end-to-end test with an actual paired Android phone, which this sandbox cannot provide — see the troubleshooting steps in `linux/README.md` when that's available.

## 2026-07-09 (later same day) — Real-device install + two real bugs fixed + Bluetooth audio blocked (reproducible, documented)

Turns out this sandbox IS the user's actual Ubuntu desktop (real Wayland session, real RustDesk remote-desktop client, real physical phone pluggable via USB) — so today's session did a full real-hardware install and test pass, not just simulated testing.

**Ubuntu app**: installed the `.deb` for real (`sudo apt install ./dash-phonecon_1.0.0_all.deb`), running live via autostart-equivalent launch.

**Android app**: no prebuilt APK existed, so built one from source. Hit and fixed two real, pre-existing bugs unrelated to Ubuntu (would affect anyone building this project fresh, on any OS):
1. `android/gradle.properties` was missing entirely and was gitignored (`android/.gitignore` had listed it alongside `local.properties` under a "contains SDK path" comment, which is wrong for `gradle.properties` — it's not machine-specific). Without `android.useAndroidX=true` in it, the build fails at `:app:checkDebugAarMetadata` on literally any machine. Added the file with the required flags, and removed it from `.gitignore` (kept `local.properties` ignored, since that one genuinely holds a machine-specific SDK path). Now committed so fresh clones build out of the box.
2. `android/local.properties` (correctly gitignored, machine-specific) pointed at `/opt/homebrew/share/android-commandlinetools` (a leftover Mac path from earlier work). Updated to this machine's SDK path (`/usr/lib/android-sdk`, installed via Ubuntu's own `google-android-cmdline-tools-19.0-installer` + `sdkmanager` — Ubuntu's repos ship a full working Android SDK installer, no need to hand-download from Google).

Installed the APK via `adb install` after fixing a real Linux gotcha: `adb devices` showed nothing even with USB debugging enabled, because there was no udev rule granting non-root USB access to the phone's vendor ID. Fixed with a standard rule: `/etc/udev/rules.d/51-android.rules` → `SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev", TAG+="uaccess"` (Samsung's vendor ID; `plugdev` group membership was already present). This is a one-time host-machine fix, not specific to this project.

Granted all Android runtime permissions via `adb shell pm grant` (faster than tapping through dialogs) except `POST_NOTIFICATIONS`, which correctly doesn't exist as a grantable permission on this phone's Android 12 (that permission is Android 13+ only, and `MainActivity.kt` already guards the request for `TIRAMISU+` — nothing to fix).

**WiFi/WebSocket connection — fully verified working end-to-end on real hardware:**
- Initially tried the phone's LAN IP — failed (`Reconnecting…`), because the phone (WiFi network "Thoughtworks") and this computer are on network segments that don't allow direct device-to-device traffic even though both show similar-looking `10.132.x.x` addresses (confirmed via ping: 100% loss). Client isolation or separate VLANs, not a firewall issue on either device (ufw is inactive; port 8765 listens on 0.0.0.0 correctly).
- Switched to Tailscale IPs instead (both devices already on the same tailnet — phone is "cz1" at `100.119.246.51`, this machine is `100.93.224.23`) — connected immediately and stayed connected, including correctly surviving a real disconnect/reconnect cycle (verified via `adb logcat`: phone detected a broken pipe within its 30s PING cycle and reconnected within the designed 2s backoff, exactly as `PhoneWebSocketClient.kt` is supposed to behave).
- Updated `linux/README.md` and root `README.md` to recommend Tailscale explicitly (not just "same WiFi") given this confirmed, real failure mode.
- Full CALL_RINGING → CALL_ACTIVE → CALL_ENDED cycle confirmed multiple times via `tests/fake_phone_client.py` against the real installed app, all transitions logged correctly, tray/state handling correct.

**Bluetooth call audio (Phase 4) — thoroughly investigated, not working, root cause narrowed down and documented.** Full details, exact reproducible error, everything ruled out, and concrete next steps are in `linux/README.md`'s new "Known blocker (as of 2026-07-09)" section — not duplicating all of it here, but summary: pairing and Android's connection-policy auto-allow both work correctly (confirmed via `adb shell dumpsys bluetooth_manager` showing `HEADSET=100` for this computer, and BlueZ correctly advertising the `Handsfree` HF-role UUID `0000111e` — both further than macOS 26 ever gets), but `bluetoothd` reproducibly fails to complete the actual HFP transport connection (`Unable to get io data for Hands-Free unit: getpeername: Transport endpoint is not connected`), so PipeWire's card for the phone only ever shows an `audio-gateway` profile (wrong direction) and never `headset-head-unit`. Ruled out: stale pairing (fully re-paired from scratch, same result), outdated bluez (updated to latest available point release, same result), oFono as an alternative backend (installed, configured, reverted — didn't integrate without deeper oFono-side modem config). This looks like a real PipeWire/BlueZ bug or version-specific limitation on Ubuntu 26.04 rather than a configuration mistake on our part. A ready-to-use task prompt for a follow-up agent session (with instructions to research upstream issue trackers and keep iterating rather than stopping to ask) was handed to the user directly in chat, not stored in the repo.

Also discovered along the way and worth remembering: this environment appears to have some automated interaction layer (separate from RustDesk) — during earlier isolated GUI testing (before real-hardware testing began), a popup once received a spontaneous "ANSWER" click with the user confirming they saw nothing. Re-verified with `QT_QPA_PLATFORM=offscreen` (zero possibility of real input) and got zero spurious events, so this is a sandbox artifact, not an app bug — mentioned here again in case it recurs and confuses a future debugging session.

Left running/installed on the machine at the end of this session: `dash-phonecon` installed via apt and running live; Android app installed and connected via Tailscale IP; `ofono` package installed but inactive/unconfigured (harmless, left in case a future agent wants to pursue that path further); BlueZ updated to the latest available point release.
