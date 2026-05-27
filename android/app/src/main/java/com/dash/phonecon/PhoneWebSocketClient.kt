package com.dash.phonecon

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

private const val TAG = "PhoneWebSocketClient"
private const val PING_INTERVAL_SECONDS = 30L
private const val RECONNECT_DELAY_MIN_SECONDS = 2L
private const val RECONNECT_DELAY_MAX_SECONDS = 60L
private const val NORMAL_CLOSE_CODE = 1000

interface WebSocketCallback {
    fun onMessage(msg: String)
    fun onConnected()
    fun onDisconnected()
}

class PhoneWebSocketClient(private val callback: WebSocketCallback) {

    private val httpClient = OkHttpClient.Builder()
        .pingInterval(0, TimeUnit.SECONDS)
        .build()

    private val scheduler: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor()

    private var webSocket: WebSocket? = null
    private var macIp: String = ""
    private var pingTask: ScheduledFuture<*>? = null
    private var reconnectTask: ScheduledFuture<*>? = null
    private var reconnectDelaySec = RECONNECT_DELAY_MIN_SECONDS

    private val connected = AtomicBoolean(false)
    private val intentionallyStopped = AtomicBoolean(false)

    val isConnected: Boolean get() = connected.get()

    fun connect(ip: String) {
        macIp = ip
        intentionallyStopped.set(false)
        reconnectDelaySec = RECONNECT_DELAY_MIN_SECONDS
        openSocket()
    }

    fun disconnect() {
        intentionallyStopped.set(true)
        cancelReconnect()
        cancelPing()
        webSocket?.close(NORMAL_CLOSE_CODE, "User stopped service")
        webSocket = null
        connected.set(false)
    }

    fun send(message: String) {
        if (!connected.get()) {
            Log.w(TAG, "Attempted send while disconnected — dropping message")
            return
        }
        webSocket?.send(message)
    }

    fun resetPingTimer() {
        cancelPing()
        schedulePing()
    }

    private fun openSocket() {
        val url = "ws://$macIp:8765"
        val request = Request.Builder().url(url).build()
        webSocket = httpClient.newWebSocket(request, socketListener)
        Log.d(TAG, "Connecting to $url")
    }

    private val socketListener = object : WebSocketListener() {

        override fun onOpen(ws: WebSocket, response: Response) {
            connected.set(true)
            reconnectDelaySec = RECONNECT_DELAY_MIN_SECONDS
            cancelReconnect()
            schedulePing()
            Log.d(TAG, "WebSocket connected")
            callback.onConnected()
        }

        override fun onMessage(ws: WebSocket, text: String) {
            resetPingTimer()
            callback.onMessage(text)
        }

        override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
            Log.e(TAG, "WebSocket failure: ${t.message}")
            handleDisconnection()
        }

        override fun onClosed(ws: WebSocket, code: Int, reason: String) {
            Log.d(TAG, "WebSocket closed: $code $reason")
            handleDisconnection()
        }
    }

    private fun handleDisconnection() {
        val wasConnected = connected.getAndSet(false)
        cancelPing()

        if (wasConnected) {
            callback.onDisconnected()
        }

        if (!intentionallyStopped.get()) {
            scheduleReconnect()
        }
    }

    private fun schedulePing() {
        pingTask = scheduler.scheduleAtFixedRate(
            { sendPing() },
            PING_INTERVAL_SECONDS,
            PING_INTERVAL_SECONDS,
            TimeUnit.SECONDS
        )
    }

    private fun sendPing() {
        val ping = JSONObject().put(MessageType.FIELD_TYPE, MessageType.PING).toString()
        webSocket?.send(ping)
        Log.d(TAG, "PING sent")
    }

    private fun cancelPing() {
        pingTask?.cancel(false)
        pingTask = null
    }

    private fun scheduleReconnect() {
        Log.d(TAG, "Reconnecting in ${reconnectDelaySec}s")
        reconnectTask = scheduler.schedule(
            {
                if (!intentionallyStopped.get()) {
                    openSocket()
                }
            },
            reconnectDelaySec,
            TimeUnit.SECONDS
        )
        reconnectDelaySec = minOf(reconnectDelaySec * 2, RECONNECT_DELAY_MAX_SECONDS)
    }

    private fun cancelReconnect() {
        reconnectTask?.cancel(false)
        reconnectTask = null
    }
}
