import Foundation
import Combine

enum CallState {
    case idle
    case ringing(number: String, name: String)
    case active(startTime: Date)
}

@MainActor
final class CallStateViewModel: ObservableObject {
    @Published var callState: CallState = .idle

    private var server: CallServer?
    private var hfpManager: HFPManager?
    private var popupWindow: CallPopupWindow?

    func attach(server: CallServer) {
        self.server = server
    }

    func attach(hfpManager: HFPManager) {
        self.hfpManager = hfpManager
    }

    func handleEvent(_ json: [String: Any]) {
        guard let typeRaw = json["type"] as? String,
              let messageType = MessageType(rawValue: typeRaw) else { return }

        switch messageType {
        case .callRinging:
            let number = json["number"] as? String ?? ""
            let name = json["name"] as? String ?? ""
            callState = .ringing(number: number, name: name)
            showPopup(number: number, name: name)

        case .callActive:
            callState = .active(startTime: Date())
            closePopup()
            hfpManager?.openAudio()

        case .callEnded:
            callState = .idle
            closePopup()
            hfpManager?.closeAudio()

        case .ping:
            sendCommand(.pong)

        default:
            break
        }
    }

    func sendCommand(_ type: MessageType) {
        let payload: [String: Any] = ["type": type.rawValue]
        server?.send(json: payload)
    }

    private func showPopup(number: String, name: String) {
        if popupWindow == nil {
            popupWindow = CallPopupWindow(viewModel: self)
        }
        popupWindow?.show(number: number, name: name)
    }

    func closePopup() {
        popupWindow?.close()
        popupWindow = nil
    }
}
