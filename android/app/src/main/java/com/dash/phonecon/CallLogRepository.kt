package com.dash.phonecon

import android.content.Context
import android.provider.CallLog
import org.json.JSONArray
import org.json.JSONObject

/** Reads recent call history from the phone's real CallLog provider
 * (android.provider.CallLog) - same permission (READ_CALL_LOG) this app
 * already holds for caller-name lookups on incoming calls. */
object CallLogRepository {

    data class Entry(val number: String, val name: String, val callType: Int, val timestamp: Long, val duration: Long)

    private const val MAX_ENTRIES = 100

    fun recent(context: Context): List<Entry> {
        val entries = mutableListOf<Entry>()
        val projection = arrayOf(
            CallLog.Calls.NUMBER,
            CallLog.Calls.CACHED_NAME,
            CallLog.Calls.TYPE,
            CallLog.Calls.DATE,
            CallLog.Calls.DURATION,
        )
        context.contentResolver.query(
            CallLog.Calls.CONTENT_URI,
            projection,
            null,
            null,
            "${CallLog.Calls.DATE} DESC LIMIT $MAX_ENTRIES",
        )?.use { cursor ->
            val numberIdx = cursor.getColumnIndexOrThrow(CallLog.Calls.NUMBER)
            val nameIdx = cursor.getColumnIndexOrThrow(CallLog.Calls.CACHED_NAME)
            val typeIdx = cursor.getColumnIndexOrThrow(CallLog.Calls.TYPE)
            val dateIdx = cursor.getColumnIndexOrThrow(CallLog.Calls.DATE)
            val durationIdx = cursor.getColumnIndexOrThrow(CallLog.Calls.DURATION)
            while (cursor.moveToNext()) {
                entries.add(
                    Entry(
                        number = cursor.getString(numberIdx) ?: "",
                        name = cursor.getString(nameIdx) ?: "",
                        callType = cursor.getInt(typeIdx),
                        timestamp = cursor.getLong(dateIdx),
                        duration = cursor.getLong(durationIdx),
                    )
                )
            }
        }
        return entries
    }

    fun toJsonArray(entries: List<Entry>): JSONArray {
        val array = JSONArray()
        for (entry in entries) {
            array.put(
                JSONObject()
                    .put(MessageType.FIELD_NUMBER, entry.number)
                    .put(MessageType.FIELD_NAME, entry.name)
                    .put(MessageType.FIELD_CALL_TYPE, entry.callType)
                    .put(MessageType.FIELD_TIMESTAMP, entry.timestamp)
                    .put(MessageType.FIELD_DURATION, entry.duration)
            )
        }
        return array
    }
}
