# Dash Phone Con — Ubuntu

Answer and control your Android phone's calls from Ubuntu: when your
phone rings, a popup appears in the corner of your screen with the
caller's name and number. Answer, decline, or hang up without touching
your phone. A system tray icon shows whether the phone is connected and
whether a call is ringing or active.

This is the Ubuntu counterpart to the macOS app in `../macos/` — both
speak the exact same WiFi protocol to the same Android app in `../android/`
(see `../PLAN.md`), so the Android app needs **no changes** to work with
Ubuntu instead of a Mac. Only the "Mac IP Address" field's label on Android
is a leftover name; type your Ubuntu machine's IP into it, same as you
would a Mac's.

📖 See the [full documentation site](https://shrijayan.github.io/dash-phonecon/docs/ubuntu/install) for install, first-run, and troubleshooting guides.

## What works

| Feature | Status |
|---|---|
| Incoming call popup with caller name + number | Works |
| Answer / Decline from Ubuntu | Works |
| Hang up an active call from Ubuntu | Works |
| Active call timer + connection status in the tray | Works |
| Auto-reconnect on the phone side (already built into the Android app) | Works |
| Other media (Spotify, browser tabs, etc.) pauses automatically during a call | Best-effort - see [Media ducking](#media-ducking-best-effort) |
| Call audio through this computer's speakers/mic (Bluetooth Hands-Free) | Best-effort - see [Bluetooth call audio](#bluetooth-call-audio-best-effort) |
| Wireless screen mirroring (see the phone's screen, click to control) | Works - see [Screen share](#screen-share) |

Unlike macOS 26 (which removed the API this needs - see `../README.md`),
Ubuntu's audio system (PipeWire) has a real, non-blocked path for this, but
it still depends on your specific phone's Android/OEM Bluetooth stack
cooperating. Everything else in this list works independently of
Bluetooth entirely, over WiFi.

## How it works (short version)

1. Your phone and this computer must be on the same WiFi network (or a
   VPN like Tailscale).
2. This app listens for the phone on `0.0.0.0:8765` (WebSocket).
3. The phone sends small JSON messages like `{"type": "CALL_RINGING", ...}`
   when it rings; this app replies with `{"type": "ANSWER"}` etc. when you
   click a button. See `../PLAN.md` for the full message list.
4. Nothing here can *dial out* from Ubuntu - it only reacts to calls that
   are already happening on the phone.

## Install

### Option A: one-line install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/shrijayan/dash-phonecon/main/linux/install.sh | bash
```

Downloads the latest `.deb` release from GitHub, verifies its SHA-256
checksum, and installs it with `apt` (which pulls in PySide6 and every
other dependency automatically). To install a specific version instead
of latest: `... | bash -s -- --version 1.2.0`.

### Option B: build and install the .deb yourself

```bash
cd linux
./build-deb.sh
sudo apt install ./dist/dash-phonecon_*_all.deb
```

This installs:
- the app to `/usr/lib/python3/dist-packages/dashphone/`
- a `dash-phonecon` command to `/usr/bin/`
- an app-menu entry and an autostart entry (starts automatically next
  time you log in - look for the tray icon)

Start it immediately without logging out: `dash-phonecon &`

Uninstall: `sudo apt remove dash-phonecon`

### Option C: run from source (for development)

```bash
cd linux
sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets python3-websockets
PYTHONPATH=src python3 -m dashphone
```

## First-time setup

1. Install this app on Ubuntu (above) and the Android app on your phone
   (`../android/`).
2. Make sure both devices can reach each other - either:
   - **Same local WiFi network** (simplest, no extra setup), or
   - **Tailscale** (recommended if your phone is ever on a different
     network than this computer, e.g. mobile data, a different WiFi, or
     a network with client isolation that blocks device-to-device LAN
     traffic even when "on the same WiFi"). Install the Tailscale app on
     the phone and sign into the same tailnet as this computer - then use
     this computer's Tailscale IP (`tailscale ip -4`) instead of its LAN
     IP in the next step. This is the confirmed working setup for this
     project - the WebSocket server listens on all interfaces (`0.0.0.0`),
     so it accepts connections from either.
3. Open the tray icon menu - it shows "This device: `<ip>`:8765" (your LAN
   IP). Type either that IP or your Tailscale IP into the Android app's IP
   field and tap Start.
4. The tray icon turns from grey to its connected colour.

## Media ducking (best-effort)

While a call is active, this app pauses whatever else was playing audio
(Spotify, a YouTube tab, VLC, etc.) via the standard MPRIS2 D-Bus interface
(`org.mpris.MediaPlayer2.*`) that most Linux media players implement -
nothing player-specific to configure. Only players that were actually
*playing* when the call started are paused, and only those same players
are resumed when the call ends (anything already paused, or opened during
the call, is left alone).

This needs no Bluetooth and no phone-side setup - it works over the same
WiFi/Tailscale call-control link as the popup itself, so it works even if
[Bluetooth call audio](#bluetooth-call-audio-best-effort) is not set up or
not supported by your phone.

If a player does not get paused, check the log
(`~/.local/state/dash-phonecon/dashphone.log`) for `media_ducker` lines -
most likely that player does not implement MPRIS2, or wasn't in the
"Playing" state (e.g. a paused video) when the call started.

## Screen share

From the tray menu, click **Screen Share Phone** to open a live mirror of
the phone's screen in a window on this computer (via
[scrcpy](https://github.com/Genymobile/scrcpy)) - you can even click/type
into it to control the phone remotely, no cable required. This uses the
*same* IP address already talking to this app over WiFi/Tailscale for call
control - no second IP to type in anywhere.

### One-time phone setup: enable Wireless debugging

1. On the phone: **Settings → About phone → tap "Build number" 7 times**
   to unlock Developer options (skip if already a developer).
2. **Settings → System → Developer options → enable "Wireless debugging"**.
3. Trust this computer for wireless ADB - two ways, pick whichever your
   phone offers:
   - **No cable at all (Android 11+):** tap "Wireless debugging" →
     **"Pair device with QR code"** (or "Pair device with pairing code"),
     scan/enter it - this pairing happens entirely over WiFi.
   - **USB, once (works on any Android version):** plug in via USB and run:
     ```bash
     adb tcpip 5555
     ```
   Either way, this only needs doing again if you factory-reset the phone
   or revoke USB debugging authorizations - it survives reboots and WiFi
   reconnects.

### Requirements

Needs `scrcpy` and `adb` on this computer:

```bash
sudo apt install scrcpy adb
```

If either is missing, the tray menu item is greyed out with that reason
shown directly in the menu instead of failing silently on click.

### Auto-reconnect - no re-clicking needed

Screen share depends on the phone being reachable at its current IP over
`adb connect` - the exact same network path (LAN or Tailscale) already
used for call control, which this project is built around staying solid
across the phone roaming the house. Once you click **Screen Share Phone**,
it stays "on" until you explicitly click it again (to stop) or quit the
app:

- If the phone hasn't connected to this computer yet, it keeps retrying
  every few seconds until it does.
- If scrcpy's connection drops (phone leaves WiFi range, briefly loses
  signal, etc.), it automatically reconnects and re-launches scrcpy on
  its own the moment the phone is reachable again - no manual click
  required, matching this project's "no loss when the phone changes
  rooms" goal.
- After about a minute of continuous failures it gives up and shows
  "Failed" in the tray menu (most commonly meaning Wireless debugging
  got disabled on the phone) - click **Screen Share Phone** again to
  restart the retry loop once you've fixed that.

## Bluetooth call audio (best-effort)

To talk through this computer's speakers/mic during a call (instead of
the phone's own speaker), like Apple's Continuity Calls between iPhone
and Mac:

1. Pair this computer with your phone over Bluetooth once, the normal way
   (Settings → Bluetooth, on both sides).
2. On Android: **Settings → Connected devices → (this computer) → tap the
   gear icon → enable "Phone calls"**. Without this toggle, Android will
   never connect the Hands-Free audio profile to this computer at all.
3. That's it - no configuration needed on the Ubuntu side. When a call
   becomes active, the app looks for the phone's Bluetooth audio device
   and switches your default speaker/mic to it for the duration of the
   call, then switches back afterwards.

This depends on packages from `Recommends:` in the package (`python3-dbus`,
`pulseaudio-utils`, `bluez`, `libspa-0.2-bluetooth`) - installed by default
with the `.deb` unless you passed `--no-install-recommends`.

**This is genuinely best-effort** - some Android/OEM Bluetooth stacks
restrict the "Phone calls" toggle to devices they recognise as
headsets/car-kits, and every case is verified different. If it doesn't
work: the popup/answer/decline/hangup features above are completely
unaffected either way, since they don't use Bluetooth at all.

### If audio routing doesn't work, check the log first

```bash
tail -50 ~/.local/state/dash-phonecon/dashphone.log
```

Then, with a call active, check whether the phone actually shows up as a
Bluetooth audio device:

```bash
bluetoothctl info <phone-mac-address>   # look for "Connected: yes"
pactl list cards                        # look for a bluez_card.<mac> entry
                                         # and check its available profiles
```

If there's no `bluez_card...` entry at all while a call is active, Android
did not open a Hands-Free connection to this computer - re-check the
"Phone calls" toggle in step 2 above. If the card exists but has no
available Hands-Free profile, your phone's Bluetooth stack is not
offering that role to this computer.

### Known blocker (as of 2026-07-09): HFP Hands-Free transport fails

On a real device (Samsung Galaxy A31 / Android 12) paired with an Ubuntu
26.04 machine (PipeWire 1.6.2, WirePlumber 0.5.13, BlueZ 5.85), the
Bluetooth *pairing and policy* side works correctly, but the actual audio
profile connection does not complete:

- This computer's adapter correctly advertises the `Handsfree` (HF, HFP
  head-unit) role UUID `0000111e` (confirmed via `bluetoothctl show`) -
  this is the exact thing that is *broken* on macOS 26, so Ubuntu is
  further along than the Mac ever got.
- Android correctly recognises this and automatically sets its Bluetooth
  connection policy for this computer to `HEADSET=100` (ALLOWED) - visible
  in `adb shell dumpsys bluetooth_manager` - equivalent to the manual
  "Phone calls" toggle being on.
- Despite that, `pactl list cards` never shows a `headset-head-unit`
  profile for the phone's card - only `off` and `audio-gateway` (the
  *wrong* direction: that profile means this computer would act as the
  audio gateway for a remote headset, not the other way around).
- `journalctl -u bluetooth` shows the concrete, **100% reproducible**
  failure every time Android attempts the connection:
  ```
  bluetoothd: src/profile.c:ext_io_disconnected() Unable to get io data
  for Hands-Free unit: getpeername: Transport endpoint is not connected (107)
  ```
  (and sometimes `Unable to get Hands-Free unit SDP record: Operation
  already in progress`.) This is a transport-level failure inside
  BlueZ/PipeWire's native HFP-HF implementation, not a pairing or policy
  problem.

**Ruled out** (none of these changed the result):
- Stale pairing/link-key state - fully unpaired and re-paired from scratch
- Outdated packages - updated `bluez` to the latest point release available
- Backend choice - installed `ofono` and set
  `bluez5.hfphsp-backend = "ofono"` in
  `~/.config/wireplumber/wireplumber.conf.d/` (reverted afterwards - this
  did not produce even the transport error, i.e. it did not integrate
  automatically without further oFono-side modem/HFP configuration)

**Not yet tried / next steps for whoever picks this up:**
1. Search upstream PipeWire/BlueZ issue trackers for
   `"Unable to get io data for Hands-Free unit"` and `ext_io_disconnected`
   - this looks like a specific, nameable bug rather than a config
   problem, and may already be reported/fixed in a newer release.
2. Try a newer/older PipeWire+WirePlumber version (this is Ubuntu 26.04,
   a very new release - a point update may fix it, or an older
   well-established LTS like 24.04 may not hit the same bug).
3. Capture a full `btmon` trace across a complete connection attempt
   (see the session that found this - `sudo btmon` while toggling
   Bluetooth on the phone) and inspect the RFCOMM channel setup in detail
   to see exactly which side closes the socket.
4. Try from a second Android phone/OEM to rule out something specific to
   this Samsung device's HFP implementation.
5. Revisit the oFono path properly - oFono has explicit
   `org.ofono.Handsfree` / `org.ofono.HandsfreeAudioCard` D-Bus APIs
   designed for exactly this "be a hands-free accessory to a remote AG"
   role, but needs oFono to actually detect/bind the Bluetooth device as
   a modem, which did not happen automatically in the brief attempt above
   and would need more targeted configuration/reading of oFono's Bluetooth
   plugin docs.

The code in `src/dashphone/bluetooth/` (device discovery, `pactl`
matching/switching, retry loop) is complete, unit-tested, and confirmed to
run correctly against this exact failure mode (it detects the paired
phone, attempts the switch, times out gracefully, and never crashes the
rest of the app) - the blocker is entirely in the underlying OS Bluetooth
stack, not in this project's code.

## Uninstall

```bash
sudo apt remove dash-phonecon
```

## Project structure

```
linux/
├── build-deb.sh                  # assembles the .deb from src/
├── packaging/                    # Debian control file, postinst/postrm,
│                                  # .desktop entry, launcher script
├── src/dashphone/
│   ├── app.py                    # composition root - wires everything together
│   ├── protocol/                 # shared message-type vocabulary (see ../PLAN.md)
│   ├── state/                    # CallState + CallStateController (pure logic, no Qt widgets/network)
│   ├── network/                  # asyncio WebSocket server (port 8765) + LAN IP helper
│   ├── bluetooth/                # best-effort Bluetooth Hands-Free audio routing (Phase 4)
│   ├── screenshare/               # wireless scrcpy/adb screen mirroring
│   ├── media_ducker.py           # best-effort MPRIS pause/resume of other media during a call
│   └── ui/                       # tray icon, incoming-call popup, icon drawing
└── tests/
    ├── test_call_state.py            # unit tests for the state/protocol logic
    ├── test_audio_router_parsing.py  # unit tests for pactl JSON parsing/matching
    ├── test_media_ducker.py          # unit tests for MPRIS pause/resume matching + idempotency
    ├── test_screen_share_manager.py   # unit tests for adb/scrcpy orchestration
    └── fake_phone_client.py          # simulates the Android phone, for manual testing
```

Each layer only depends on the small interface it actually needs (a
`CallState`, a "send this JSON" function, etc.) instead of on each other's
concrete classes - see the module docstrings for what each piece owns.
This mirrors the macOS app's architecture (`CallStateViewModel` →
`CallStateController`, `CallServer` → `CallServer`, `HFPManager` →
`bluetooth/hfp_manager.py`) so both apps are easy to compare side by side.

## Development

Run the unit tests (no display, no real phone or Bluetooth needed):

```bash
cd linux
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -t . -v
```

Try the whole app against a simulated phone:

```bash
# terminal 1
PYTHONPATH=src python3 -m dashphone

# terminal 2 - rings, waits for you to click Answer/Decline, prints the result
python3 tests/fake_phone_client.py --number "+15551234567" --name "Jordan Test"

# or a fully scripted ring -> active -> ended cycle, no clicking needed
python3 tests/fake_phone_client.py --auto
```

Logs are written to `~/.local/state/dash-phonecon/dashphone.log` (rotated
automatically) as well as the terminal.

## Requirements

Tested on Ubuntu 24.04+ with Python 3.10+. Needs `python3-pyside6.*` and
`python3-websockets`, both available directly from Ubuntu's `universe`
repository (installed automatically as package dependencies - see
[Install](#install)).
