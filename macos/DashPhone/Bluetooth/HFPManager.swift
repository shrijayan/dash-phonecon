import Foundation
import IOBluetooth
import CoreAudio

@MainActor
final class HFPManager: NSObject, ObservableObject {
    @Published private(set) var status: HFPStatus = .idle

    private var pairedDeviceName: String?
    private var savedInputDevice: AudioDeviceID = 0
    private var savedOutputDevice: AudioDeviceID = 0
    private var routingActive = false

    func start() {
        log("Starting HFP manager")
        findPairedPhone()
    }

    func openAudio() {
        guard let name = pairedDeviceName, !name.isEmpty else {
            log("No paired phone found — cannot route audio")
            return
        }
        routingActive = true
        saveCurrentAudioDevices()
        log("Waiting for BT audio device '\(name)' to appear in CoreAudio")
        switchToBluetoothAudio(name: name, attempt: 1)
    }

    func closeAudio() {
        routingActive = false
        restoreAudioDevices()
    }

    // MARK: — Device discovery

    private func findPairedPhone() {
        guard let all = IOBluetoothDevice.pairedDevices() as? [IOBluetoothDevice],
              let phone = all.first(where: { isPhoneClass($0.classOfDevice) }) else {
            log("No phone-class device in paired list")
            status = .noPairedPhone
            return
        }
        pairedDeviceName = phone.name ?? ""
        log("Paired phone: \(phone.name ?? "unnamed") connected=\(phone.isConnected())")
        status = .found(name: phone.name ?? "unnamed")
    }

    private func isPhoneClass(_ cod: UInt32) -> Bool {
        (cod >> 8) & 0x1F == 0x02
    }

    // MARK: — CoreAudio routing

    private func saveCurrentAudioDevices() {
        savedInputDevice = defaultAudioDevice(isInput: true)
        savedOutputDevice = defaultAudioDevice(isInput: false)
        log("Saved audio — input: \(savedInputDevice), output: \(savedOutputDevice)")
    }

    private func restoreAudioDevices() {
        guard savedOutputDevice != 0 || savedInputDevice != 0 else { return }
        if savedOutputDevice != 0 { setDefaultAudioDevice(savedOutputDevice, isInput: false) }
        if savedInputDevice != 0 { setDefaultAudioDevice(savedInputDevice, isInput: true) }
        log("Restored original audio devices")
        savedInputDevice = 0
        savedOutputDevice = 0
    }

    private func switchToBluetoothAudio(name: String, attempt: Int) {
        guard routingActive, attempt <= 20, !name.isEmpty else { return }
        if attempt == 1 { logAllAudioDevices() }
        if let deviceID = findAudioDevice(containing: name) {
            log("Switching system audio → '\(name)' (id: \(deviceID))")
            setDefaultAudioDevice(deviceID, isInput: false)
            setDefaultAudioDevice(deviceID, isInput: true)
            status = .audioActive
        } else {
            log("'\(name)' not in CoreAudio (attempt \(attempt)/20) — retrying in 1s")
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
                self?.switchToBluetoothAudio(name: name, attempt: attempt + 1)
            }
        }
    }

    // MARK: — CoreAudio helpers

    private func logAllAudioDevices() {
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize) == noErr else { return }
        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var devices = [AudioDeviceID](repeating: 0, count: count)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize, &devices) == noErr else { return }
        log("CoreAudio devices:")
        for id in devices { log("  [\(id)] \(audioDeviceName(id) ?? "?")") }
    }

    private func findAudioDevice(containing substring: String) -> AudioDeviceID? {
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize) == noErr else { return nil }
        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var devices = [AudioDeviceID](repeating: 0, count: count)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &dataSize, &devices) == noErr else { return nil }
        return devices.first { audioDeviceName($0)?.localizedCaseInsensitiveContains(substring) == true }
    }

    private func audioDeviceName(_ deviceID: AudioDeviceID) -> String? {
        var buf = [CChar](repeating: 0, count: 256)
        var size = UInt32(buf.count)
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        guard AudioObjectGetPropertyData(deviceID, &addr, 0, nil, &size, &buf) == noErr else { return nil }
        return String(cString: buf)
    }

    private func defaultAudioDevice(isInput: Bool) -> AudioDeviceID {
        var deviceID = AudioDeviceID(0)
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var addr = AudioObjectPropertyAddress(
            mSelector: isInput ? kAudioHardwarePropertyDefaultInputDevice : kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &deviceID)
        return deviceID
    }

    private func setDefaultAudioDevice(_ deviceID: AudioDeviceID, isInput: Bool) {
        var mutableID = deviceID
        var addr = AudioObjectPropertyAddress(
            mSelector: isInput ? kAudioHardwarePropertyDefaultInputDevice : kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        let result = AudioObjectSetPropertyData(
            AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil,
            UInt32(MemoryLayout<AudioDeviceID>.size), &mutableID
        )
        if result != noErr { log("Failed to set \(isInput ? "input" : "output"): OSStatus \(result)") }
    }

    private func log(_ message: String) {
        print("[HFP] \(message)")
    }
}

// MARK: — Status

enum HFPStatus: Equatable {
    case idle
    case noPairedPhone
    case found(name: String)
    case connecting
    case connected
    case audioActive
    case error(String)
}
