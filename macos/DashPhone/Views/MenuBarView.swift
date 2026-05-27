import SwiftUI

struct MenuBarView: View {
    @ObservedObject var viewModel: CallStateViewModel
    @ObservedObject var server: CallServer

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            statusSection
            Divider()
            activeCallSection
            Button("Quit DashPhone") {
                NSApplication.shared.terminate(nil)
            }
            .keyboardShortcut("q", modifiers: .command)
        }
        .padding(8)
        .frame(minWidth: 200)
    }

    @ViewBuilder
    private var statusSection: some View {
        HStack {
            Circle()
                .fill(server.isConnected ? Color.green : Color.gray)
                .frame(width: 8, height: 8)
            Text(statusLabel)
                .font(.subheadline)
        }
    }

    @ViewBuilder
    private var activeCallSection: some View {
        if case .active(let startTime) = viewModel.callState {
            HStack {
                Image(systemName: "phone.connection")
                    .foregroundColor(.green)
                ActiveCallTimerView(startTime: startTime)
            }

            Button("Hang Up") {
                viewModel.sendCommand(.hangup)
            }
            .foregroundColor(.red)
        }
    }

    private var statusLabel: String {
        if !server.isConnected { return "Not Connected" }

        switch viewModel.callState {
        case .idle:
            return "Connected — No Active Call"
        case .ringing(_, let name):
            let display = name.isEmpty ? "Unknown" : name
            return "Ringing: \(display)"
        case .active:
            return "Call Active"
        }
    }
}
