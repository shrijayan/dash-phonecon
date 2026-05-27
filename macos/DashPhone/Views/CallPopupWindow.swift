import AppKit
import SwiftUI

@MainActor
final class CallPopupWindow {
    private var panel: NSPanel?
    private weak var viewModel: CallStateViewModel?

    init(viewModel: CallStateViewModel) {
        self.viewModel = viewModel
    }

    func show(number: String, name: String) {
        guard let viewModel else { return }

        if panel == nil {
            panel = makePanel()
        }

        guard let panel else { return }

        let popupView = CallPopupView(
            callerName: name,
            callerNumber: number,
            onAnswer: { [weak viewModel] in
                viewModel?.sendCommand(.answer)
                viewModel?.closePopup()
            },
            onDecline: { [weak viewModel] in
                viewModel?.sendCommand(.reject)
                viewModel?.closePopup()
            }
        )

        panel.contentView = NSHostingView(rootView: popupView)
        panel.setContentSize(panel.contentView!.fittingSize)

        positionNearMenuBar(panel)
        panel.orderFrontRegardless()
    }

    func close() {
        panel?.close()
        panel = nil
    }

    private func makePanel() -> NSPanel {
        let panel = NSPanel(
            contentRect: .zero,
            styleMask: [.titled, .fullSizeContentView, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.level = .floating
        panel.isFloatingPanel = true
        panel.titlebarAppearsTransparent = true
        panel.titleVisibility = .hidden
        panel.isMovableByWindowBackground = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false
        return panel
    }

    private func positionNearMenuBar(_ panel: NSPanel) {
        guard let screen = NSScreen.main else { return }

        let screenFrame = screen.visibleFrame
        let panelSize = panel.frame.size

        let topRight = NSPoint(
            x: screenFrame.maxX - panelSize.width - 16,
            y: screenFrame.maxY - panelSize.height - 16
        )

        panel.setFrameOrigin(topRight)
    }
}
