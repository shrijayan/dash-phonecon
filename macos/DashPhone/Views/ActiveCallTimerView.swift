import SwiftUI

struct ActiveCallTimerView: View {
    let startTime: Date

    var body: some View {
        TimelineView(.periodic(from: startTime, by: 1)) { context in
            Text(elapsed(from: startTime, to: context.date))
                .font(.system(.body, design: .monospaced))
                .foregroundColor(.secondary)
        }
    }

    private func elapsed(from start: Date, to now: Date) -> String {
        let total = max(0, Int(now.timeIntervalSince(start)))
        let minutes = total / 60
        let seconds = total % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}
