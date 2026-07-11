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
    const val DIAL = "DIAL"
    const val MUTE = "MUTE"

    // Contacts CRUD
    const val REQUEST_CONTACTS = "REQUEST_CONTACTS"
    const val CONTACTS_RESULT = "CONTACTS_RESULT"
    const val CONTACT_ADD = "CONTACT_ADD"
    const val CONTACT_UPDATE = "CONTACT_UPDATE"
    const val CONTACT_DELETE = "CONTACT_DELETE"
    const val CONTACT_OP_RESULT = "CONTACT_OP_RESULT"

    // Call log
    const val REQUEST_CALL_LOG = "REQUEST_CALL_LOG"
    const val CALL_LOG_RESULT = "CALL_LOG_RESULT"

    // JSON field keys
    const val FIELD_TYPE = "type"
    const val FIELD_NUMBER = "number"
    const val FIELD_NAME = "name"
    const val FIELD_CONTACTS = "contacts"
    const val FIELD_CONTACT_ID = "contact_id"
    const val FIELD_SUCCESS = "success"
    const val FIELD_ERROR = "error"
    const val FIELD_CALLS = "calls"
    const val FIELD_CALL_TYPE = "call_type"
    const val FIELD_TIMESTAMP = "timestamp"
    const val FIELD_DURATION = "duration"
    const val FIELD_MUTED = "muted"
}
