import SwiftUI

struct CallPopupView: View {
    let callerName: String
    let callerNumber: String

    let onAnswer: () -> Void
    let onDecline: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "phone.arrow.down.left")
                    .foregroundColor(.green)
                Text("Incoming Call")
                    .font(.headline)
            }

            Divider()

            VStack(spacing: 4) {
                Text(callerName.isEmpty ? "Unknown" : callerName)
                    .font(.title3)
                    .fontWeight(.semibold)

                Text(callerNumber)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Spacer().frame(height: 4)

            HStack(spacing: 16) {
                Button(action: onAnswer) {
                    Label("Answer", systemImage: "phone.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.green)
                .keyboardShortcut(.return, modifiers: [])

                Button(action: onDecline) {
                    Label("Decline", systemImage: "phone.down.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
                .keyboardShortcut(.escape, modifiers: [])
            }
        }
        .padding(20)
        .frame(width: 300)
    }
}
