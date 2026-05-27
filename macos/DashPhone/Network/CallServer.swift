import Foundation
import Network
import Combine

final class CallServer: ObservableObject {
    @Published var isConnected: Bool = false

    private static let port: NWEndpoint.Port = 8765

    private var listener: NWListener?
    private var activeConnection: NWConnection?
    private weak var viewModel: CallStateViewModel?

    @MainActor
    func start(viewModel: CallStateViewModel) {
        self.viewModel = viewModel
        viewModel.attach(server: self)
        startListener()
    }

    func send(json: [String: Any]) {
        guard let connection = activeConnection,
              let data = try? JSONSerialization.data(withJSONObject: json),
              let text = String(data: data, encoding: .utf8) else { return }

        let metadata = NWProtocolWebSocket.Metadata(opcode: .text)
        let context = NWConnection.ContentContext(identifier: "send", metadata: [metadata])

        connection.send(
            content: text.data(using: .utf8),
            contentContext: context,
            isComplete: true,
            completion: .idempotent
        )
    }

    private func startListener() {
        let params = NWParameters.tcp
        let wsOptions = NWProtocolWebSocket.Options()
        wsOptions.autoReplyPing = true
        params.defaultProtocolStack.applicationProtocols.insert(wsOptions, at: 0)

        do {
            listener = try NWListener(using: params, on: CallServer.port)
        } catch {
            fatalError("Failed to create NWListener on port \(CallServer.port): \(error)")
        }

        listener?.newConnectionHandler = { [weak self] connection in
            self?.acceptConnection(connection)
        }

        listener?.stateUpdateHandler = { state in
            if case .failed(let error) = state {
                fatalError("Listener failed: \(error)")
            }
        }

        listener?.start(queue: .main)
    }

    private func acceptConnection(_ connection: NWConnection) {
        activeConnection?.cancel()
        activeConnection = connection

        connection.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                DispatchQueue.main.async { self?.isConnected = true }
                self?.receiveNextMessage(from: connection)
            case .failed, .cancelled:
                DispatchQueue.main.async { self?.isConnected = false }
            default:
                break
            }
        }

        connection.start(queue: .main)
    }

    private func receiveNextMessage(from connection: NWConnection) {
        connection.receiveMessage { [weak self] data, _, _, error in
            if let error {
                print("WebSocket receive error: \(error)")
                return
            }

            if let data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                Task { @MainActor in
                    self?.viewModel?.handleEvent(json)
                }
            }

            self?.receiveNextMessage(from: connection)
        }
    }
}
