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
// If no PONG (or any other message) arrives within this many seconds of
// sending a PING, the TCP connection is presumed dead and we force-close
// it so reconnection actually kicks in - see PONG_TIMEOUT_SECONDS usage
// in schedulePongTimeout() for why this is needed at all.
private const val PONG_TIMEOUT_SECONDS = 15L
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
    private var pongTimeoutTask: ScheduledFuture<*>? = null
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
        cancelPongTimeout()
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
        cancelPongTimeout()
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
            // Any traffic at all (not just PONG) proves the connection is alive -
            // e.g. the phone side answers CALL_RINGING/CALL_ACTIVE without a PONG
            // in between, so gate liveness on "something arrived", not the reply type.
            cancelPongTimeout()
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
        cancelPongTimeout()

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
        schedulePongTimeout()
    }

    private fun cancelPing() {
        pingTask?.cancel(false)
        pingTask = null
    }

    /** Guards against a silently-dead TCP connection (common on flaky WiFi/
     * Tailscale links: the peer is gone but no RST/FIN ever arrives, so
     * OkHttp's onFailure()/onClosed() never fire on their own - reconnection
     * would otherwise never happen). If nothing arrives within
     * PONG_TIMEOUT_SECONDS of sending a PING, force-close the socket so
     * handleDisconnection() runs and the normal reconnect backoff kicks in. */
    private fun schedulePongTimeout() {
        pongTimeoutTask = scheduler.schedule(
            {
                Log.w(TAG, "No PONG within ${PONG_TIMEOUT_SECONDS}s - treating connection as dead")
                webSocket?.cancel()
            },
            PONG_TIMEOUT_SECONDS,
            TimeUnit.SECONDS
        )
    }

    private fun cancelPongTimeout() {
        pongTimeoutTask?.cancel(false)
        pongTimeoutTask = null
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
