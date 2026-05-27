package com.dash.phonecon

object MessageType {
    // Phone → Mac
    const val CALL_RINGING = "CALL_RINGING"
    const val CALL_ACTIVE = "CALL_ACTIVE"
    const val CALL_ENDED = "CALL_ENDED"
    const val PING = "PING"

    // Mac → Phone
    const val ANSWER = "ANSWER"
    const val REJECT = "REJECT"
    const val HANGUP = "HANGUP"
    const val PONG = "PONG"

    // JSON field keys
    const val FIELD_TYPE = "type"
    const val FIELD_NUMBER = "number"
    const val FIELD_NAME = "name"
}
