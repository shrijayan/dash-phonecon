import Foundation

enum MessageType: String {
    case callRinging = "CALL_RINGING"
    case callActive = "CALL_ACTIVE"
    case callEnded = "CALL_ENDED"
    case ping = "PING"
    case answer = "ANSWER"
    case reject = "REJECT"
    case hangup = "HANGUP"
    case pong = "PONG"
}
