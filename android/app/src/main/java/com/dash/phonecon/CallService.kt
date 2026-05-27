package com.dash.phonecon

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
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
            else -> Log.w(TAG, "Unknown command type: $type")
        }
    }

    // --- CallEventListener ---

    override fun onRinging(number: String, contactName: String?) {
        val displayName = contactName ?: number.ifEmpty { "Unknown" }
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CALL_RINGING)
            .put(MessageType.FIELD_NUMBER, number)
            .put(MessageType.FIELD_NAME, displayName)
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

    override fun onCallActive() {
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CALL_ACTIVE)
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

    override fun onCallEnded() {
        val payload = JSONObject()
            .put(MessageType.FIELD_TYPE, MessageType.CALL_ENDED)
            .toString()
        runCatching { wsClient.send(payload) }.onFailure { Log.e(TAG, "send failed: ${it.message}", it) }
    }

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
