package com.dash.phonecon

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioManager
import android.os.Build
import android.os.IBinder
import android.telecom.TelecomManager
import android.telephony.TelephonyManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import org.json.JSONObject

private const val TAG = "CallService"
private const val NOTIFICATION_ID = 1
private const val CHANNEL_ID = "dash_phonecon_channel"

const val ACTION_STATUS_BROADCAST = "com.dash.phonecon.STATUS"
const val EXTRA_STATUS = "status"

enum class ConnectionStatus { CONNECTED, DISCONNECTED, RECONNECTING }

class CallService : Service(), WebSocketCallback, CallEventListener {

    private lateinit var wsClient: PhoneWebSocketClient
    private lateinit var phoneReceiver: PhoneStateReceiver
    private lateinit var localBroadcast: LocalBroadcastManager

    override fun onCreate() {
        super.onCreate()
        localBroadcast = LocalBroadcastManager.getInstance(this)
        wsClient = PhoneWebSocketClient(this)
        phoneReceiver = PhoneStateReceiver(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP_SERVICE) {
            stopSelf()
            return START_NOT_STICKY
        }

        val macIp = intent?.getStringExtra(EXTRA_MAC_IP) ?: loadSavedIp()
        if (macIp.isNullOrEmpty()) {
            Log.w(TAG, "No mac_ip available — stopping service")
            stopSelf()
            return START_NOT_STICKY
        }

        startForeground(NOTIFICATION_ID, buildNotification())
        registerReceiver(phoneReceiver, IntentFilter(TelephonyManager.ACTION_PHONE_STATE_CHANGED))
        wsClient.connect(macIp)

        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        wsClient.disconnect()
        try {
            unregisterReceiver(phoneReceiver)
        } catch (e: IllegalArgumentException) {
            Log.w(TAG, "Receiver was not registered — safe to ignore")
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // --- WebSocketCallback ---

    override fun onConnected() {
        Log.d(TAG, "WebSocket connected")
        broadcastStatus(ConnectionStatus.CONNECTED)
    }

    override fun onDisconnected() {
        Log.d(TAG, "WebSocket disconnected — will reconnect")
        broadcastStatus(ConnectionStatus.RECONNECTING)
    }

    override fun onMessage(msg: String) {
        val json = runCatching { JSONObject(msg) }.getOrElse {
            Log.e(TAG, "Received non-JSON message: $msg")
            return
        }
        val type = json.optString(MessageType.FIELD_TYPE)
        Log.d(TAG, "Received command: $type")

        val mainHandler = android.os.Handler(android.os.Looper.getMainLooper())
        when (type) {
            MessageType.PONG -> wsClient.resetPingTimer()
            MessageType.ANSWER -> mainHandler.post { answerCall() }
            MessageType.REJECT, MessageType.HANGUP -> mainHandler.post { endCall() }
            MessageType.MUTE -> {
                val muted = json.optBoolean(MessageType.FIELD_MUTED)
                mainHandler.post { setMicMuted(muted) }
            }
            MessageType.DIAL -> {
                val number = json.optString(MessageType.FIELD_NUMBER)
                if (number.isNotEmpty()) {
                    mainHandler.post { dialCall(number) }
                } else {
                    Log.w(TAG, "DIAL received with no number - ignoring")
                }
            }
            MessageType.REQUEST_CONTACTS -> mainHandler.post { sendContactsList() }
            MessageType.REQUEST_CALL_LOG -> mainHandler.post { sendCallLog() }
            MessageType.CONTACT_ADD -> mainHandler.post {
                val name = json.optString(MessageType.FIELD_NAME)
                val number = json.optString(MessageType.FIELD_NUMBER)
                runCatching { ContactsRepository.add(this, name, number) }
                    .fold(
                        onSuccess = { sendContactOpResult(true, null); sendContactsList() },
                        onFailure = { sendContactOpResult(false, it.message) }
                    )
            }
            MessageType.CONTACT_UPDATE -> mainHandler.post {
                val id = json.optString(MessageType.FIELD_CONTACT_ID)
                val name = json.optString(MessageType.FIELD_NAME)
                val number = json.optString(MessageType.FIELD_NUMBER)
                runCatching { ContactsRepository.update(this, id, name, number) }
                    .fold(
                        onSuccess = { ok -> sendContactOpResult(ok, if (ok) null else "Contact not found"); sendContactsList() },
                        onFailure = { sendContactOpResult(false, it.message) }
                    )
            }
            MessageType.CONTACT_DELETE -> mainHandler.post {
                val id = json.optString(MessageType.FIELD_CONTACT_ID)
                runCatching { ContactsRepository.delete(this, id) }
                    .fold(
                        onSuccess = { ok -> sendContactOpResult(ok, if (ok) null else "Contact not found"); sendContactsList() },
                        onFailure = { sendContactOpResult(false, it.message) }
                    )
            }
            else -> Log.w(TAG, "Unknown command type: $type")
        }
    }

    // --- CallEventListener ---

    override fun onRinging(number: String, contactName: String?) {
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CALL_RINGING)
            .put(MessageType.FIELD_NUMBER, number)
            .put(MessageType.FIELD_NAME, contactName ?: "")
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

    override fun onCallActive() {
        logAudioDiagnostics("CALL_ACTIVE")
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CALL_ACTIVE)
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

    /** One-shot audio-state dump to diagnose "far end hears an echo of themselves" -
     * logs Android's actual call audio routing state so we can tell whether this is
     * speakerphone-on-acoustic-leak, a wrong AudioManager mode, or something else,
     * instead of guessing. Never throws - diagnostics must never break call handling. */
    private fun logAudioDiagnostics(trigger: String) {
        runCatching {
            val audioManager = getSystemService(AudioManager::class.java)
            val modeStr = when (audioManager.mode) {
                AudioManager.MODE_NORMAL -> "MODE_NORMAL"
                AudioManager.MODE_RINGTONE -> "MODE_RINGTONE"
                AudioManager.MODE_IN_CALL -> "MODE_IN_CALL"
                AudioManager.MODE_IN_COMMUNICATION -> "MODE_IN_COMMUNICATION"
                else -> "MODE_${audioManager.mode}"
            }
            Log.i(
                TAG,
                "[audio-diag] $trigger: mode=$modeStr isSpeakerphoneOn=${audioManager.isSpeakerphoneOn} " +
                    "isMicrophoneMute=${audioManager.isMicrophoneMute} isBluetoothScoOn=${audioManager.isBluetoothScoOn} " +
                    "isBluetoothA2dpOn=${audioManager.isBluetoothA2dpOn} isWiredHeadsetOn=${audioManager.isWiredHeadsetOn} " +
                    "streamVolume(VOICE_CALL)=${audioManager.getStreamVolume(AudioManager.STREAM_VOICE_CALL)}/" +
                    "${audioManager.getStreamMaxVolume(AudioManager.STREAM_VOICE_CALL)}"
            )
        }.onFailure { Log.w(TAG, "[audio-diag] Could not capture audio diagnostics: ${it.message}") }
    }

    override fun onCallEnded() {
        setMicMuted(false)
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CALL_ENDED)
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

    // --- Bluetooth audio routing ---
    //
    // startBluetoothSco()/stopBluetoothSco() used to be called unconditionally
    // on every CALL_ACTIVE/CALL_ENDED to hand call audio off to the Ubuntu/Mac
    // client over Bluetooth HFP. Removed entirely (2026-07-11): live logcat
    // during a real call showed the Bluetooth handoff NEVER actually completes
    // (isBluetoothScoOn stays false, activeBluetoothDevice stays null - see
    // linux/README.md's known BlueZ/PipeWire "audio-gateway" transport bug),
    // yet calling startBluetoothSco() still flips AudioManager's mode to
    // MODE_IN_COMMUNICATION and re-requests the audio focus/session, which
    // stomps on whatever echo-cancellation/audio session the actual calling
    // app (dialer or a VoIP app like WhatsApp) had already set up. That
    // session disruption - not any Bluetooth/PC audio path - is what was
    // producing the "the other person hears themselves echoed" reports,
    // confirmed via [audio-diag] logs showing SCO requested twice per call
    // with isBluetoothScoOn never turning true. Since the feature never once
    // worked end-to-end, removing the calls entirely (rather than guarding
    // them) is the safe fix until the underlying BlueZ/PipeWire bug is fixed
    // upstream - re-add only once routing has been confirmed to actually
    // succeed on a real device.

    // --- Call control ---

    private fun answerCall() {
        val telecomManager = getSystemService(TelecomManager::class.java)
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                @Suppress("DEPRECATION")
                telecomManager.acceptRingingCall()
            }
        }.onFailure { Log.e(TAG, "Failed to answer call: ${it.message}") }
    }

    private fun endCall() {
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val telecomManager = getSystemService(TelecomManager::class.java)
                telecomManager.endCall()
            } else {
                endCallViaReflection()
            }
        }.onFailure { Log.e(TAG, "Failed to end call: ${it.message}") }
    }

    private fun endCallViaReflection() {
        val telephonyManager = getSystemService(TelephonyManager::class.java)
        val method = telephonyManager.javaClass.getDeclaredMethod("endCall")
        method.isAccessible = true
        method.invoke(telephonyManager)
    }

    private fun dialCall(number: String) {
        runCatching {
            val telecomManager = getSystemService(TelecomManager::class.java)
            val uri = android.net.Uri.fromParts("tel", number, null)
            val extras = android.os.Bundle()
            telecomManager.placeCall(uri, extras)
        }.onFailure { Log.e(TAG, "Failed to place outgoing call: ${it.message}") }
    }

    private fun setMicMuted(muted: Boolean) {
        runCatching {
            getSystemService(AudioManager::class.java).isMicrophoneMute = muted
        }.onFailure { Log.e(TAG, "Failed to set mic mute: ${it.message}") }
    }

    // --- Contacts CRUD ---

    private fun sendContactsList() {
        runCatching {
            val contacts = ContactsRepository.listAll(this)
            val payload = JSONObject()
                .put(MessageType.FIELD_TYPE, MessageType.CONTACTS_RESULT)
                .put(MessageType.FIELD_CONTACTS, ContactsRepository.toJsonArray(contacts))
                .toString()
            wsClient.send(payload)
        }.onFailure { Log.e(TAG, "Failed to read contacts: ${it.message}", it) }
    }

    private fun sendContactOpResult(success: Boolean, error: String?) {
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CONTACT_OP_RESULT)
            .put(MessageType.FIELD_SUCCESS, success)
            .apply { if (error != null) put(MessageType.FIELD_ERROR, error) }
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

    // --- Call log ---

    private fun sendCallLog() {
        runCatching {
            val entries = CallLogRepository.recent(this)
            val payload = JSONObject()
                .put(MessageType.FIELD_TYPE, MessageType.CALL_LOG_RESULT)
                .put(MessageType.FIELD_CALLS, CallLogRepository.toJsonArray(entries))
                .toString()
            wsClient.send(payload)
        }.onFailure { Log.e(TAG, "Failed to read call log: ${it.message}", it) }
    }

    // --- Notifications ---

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW
        )
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        val stopIntent = Intent(this, CallService::class.java).apply {
            action = ACTION_STOP_SERVICE
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(getString(R.string.notification_text))
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .addAction(android.R.drawable.ic_delete, getString(R.string.action_stop), stopPendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun broadcastStatus(status: ConnectionStatus) {
        val intent = Intent(ACTION_STATUS_BROADCAST).putExtra(EXTRA_STATUS, status.name)
        localBroadcast.sendBroadcast(intent)
    }

    private fun loadSavedIp(): String? =
        getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).getString(PREF_MAC_IP, null)

    companion object {
        const val EXTRA_MAC_IP = "mac_ip"
        const val ACTION_STOP_SERVICE = "com.dash.phonecon.STOP_SERVICE"
        private const val PREFS_NAME = "dash_phonecon_prefs"
        private const val PREF_MAC_IP = "mac_ip"
    }
}
