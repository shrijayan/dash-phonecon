import SwiftUI

@main
struct DashPhoneApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        MenuBarExtra {
            MenuBarView(
                viewModel: appDelegate.viewModel,
                server: appDelegate.server
            )
        } label: {
            MenuBarIconView(
                viewModel: appDelegate.viewModel,
                server: appDelegate.server
            )
        }
    }
}

private struct MenuBarIconView: View {
    @ObservedObject var viewModel: CallStateViewModel
    @ObservedObject var server: CallServer

    var body: some View {
        Image(systemName: iconName)
    }

    private var iconName: String {
        if !server.isConnected { return "phone" }

        switch viewModel.callState {
        case .idle:
            return "phone.fill"
        case .ringing:
            return "phone.arrow.down.left"
        case .active:
            return "phone.connection"
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    let server = CallServer()
    let viewModel = CallStateViewModel()

    @MainActor
    func applicationDidFinishLaunching(_ notification: Notification) {
        server.start(viewModel: viewModel)
    }
}
