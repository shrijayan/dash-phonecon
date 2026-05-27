# DashPhone — Xcode Project Setup

## Prerequisites
- Xcode 15+ (for Swift 5.9 and macOS 13 SDK)
- macOS 13+ deployment target

---

## Step 1 — Create the Xcode Project

1. Open Xcode → **File → New → Project**
2. Select **macOS** tab → choose **App** template → click **Next**
3. Fill in project options:
   - **Product Name:** `DashPhone`
   - **Team:** your Apple developer team (or "None" for local builds)
   - **Organization Identifier:** `com.dash`
   - **Bundle Identifier:** `com.dash.dashphone` (auto-filled)
   - **Interface:** `SwiftUI`
   - **Language:** `Swift`
   - Uncheck "Include Tests" (optional)
4. Save the project **inside** `dash-phonecon/macos/` — Xcode will create `macos/DashPhone.xcodeproj`

---

## Step 2 — Replace Generated Files with Source Files

Xcode generates a `ContentView.swift` and an `<AppName>App.swift`. Delete them (move to Trash when prompted).

Then add all the files from `macos/DashPhone/` to the Xcode target:

1. In the **Project Navigator**, right-click the `DashPhone` group → **Add Files to "DashPhone"**
2. Select all Swift files and subdirectories, making sure **"Add to targets: DashPhone"** is checked:
   ```
   DashPhoneApp.swift
   Info.plist
   DashPhone.entitlements
   Models/
     MessageType.swift
     CallStateViewModel.swift
   Network/
     CallServer.swift
   Views/
     MenuBarView.swift
     CallPopupWindow.swift
     CallPopupView.swift
     ActiveCallTimerView.swift
   ```
3. Click **Add**

> Tip: Add folders as **groups** (not folder references) so Xcode tracks individual files.

---

## Step 3 — Configure Build Settings

### 3a. Deployment Target
1. Click the project root in the Navigator → select the **DashPhone** target → **General** tab
2. Set **Minimum Deployments → macOS** to **13.0**

### 3b. Bundle Identifier
Under **General → Identity**, confirm:
- **Bundle Identifier:** `com.dash.dashphone`

### 3c. Info.plist
1. In **Build Settings**, search for `Info.plist File`
2. Set the value to `DashPhone/Info.plist` (relative to the project root)
3. The `LSUIElement` key in the plist suppresses the Dock icon — confirm it reads `<true/>`

### 3d. Entitlements
1. Go to **Signing & Capabilities** tab
2. Click **+ Capability** → add **App Sandbox**
3. Under App Sandbox, enable:
   - **Network → Incoming Connections (Server)**
   - **Network → Outgoing Connections (Client)**
4. Xcode will link an entitlements file. If it creates a new one, delete it and instead:
   - In **Build Settings**, search for `Code Signing Entitlements`
   - Set the value to `DashPhone/DashPhone.entitlements`

---

## Step 4 — Signing

- For local development, select **Automatically manage signing** and pick your personal team.
- If you don't have a paid developer account, choose **Sign to Run Locally** (available in Xcode 16+) or disable signing for Debug builds.

---

## Step 5 — Build & Run

1. Select the **DashPhone** scheme and **My Mac** destination
2. Press **⌘R** to build and run
3. The app will appear only as a menu bar icon (phone symbol) — no Dock icon, no window
4. The WebSocket server starts on port **8765** immediately after launch

> **No external dependencies needed.** The server uses `NWProtocolWebSocket` from Apple's `Network.framework` (macOS 13+), which handles the HTTP upgrade handshake and WebSocket framing natively.

---

## Verifying the Server

Install `websocat` (a WebSocket command-line client):

```bash
brew install websocat
```

Connect and send a test event:

```bash
websocat ws://localhost:8765
```

Then paste a JSON event and press Enter:

```json
{"type":"CALL_RINGING","number":"+15551234567","name":"John Doe"}
```

A popup should appear in the top-right of your screen.

Send a ping:

```json
{"type":"PING"}
```

You should receive back:

```json
{"type":"PONG"}
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Popup does not appear | Check `LSUIElement` is `<true/>` in Info.plist; the panel requires no dock activation |
| Port 8765 already in use | `lsof -i :8765` to find the occupying process |
| Sandbox network error | Confirm both `network.server` and `network.client` are `<true/>` in entitlements |
| `MenuBarExtra` not available | Requires macOS 13+ SDK — check deployment target |
