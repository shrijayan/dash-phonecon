package com.dash.phonecon

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager

private const val PREFS_NAME = "dash_phonecon_prefs"
private const val PREF_MAC_IP = "mac_ip"
private const val REQUEST_PERMISSIONS = 100

class MainActivity : AppCompatActivity() {

    private lateinit var ipEditText: EditText
    private lateinit var toggleButton: Button
    private lateinit var statusText: TextView
    private lateinit var crashLogButton: Button
    private lateinit var crashLogText: TextView
    private lateinit var localBroadcast: LocalBroadcastManager

    private var serviceRunning = false

    private val statusReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val statusName = intent.getStringExtra(EXTRA_STATUS) ?: return
            val status = runCatching { ConnectionStatus.valueOf(statusName) }.getOrNull() ?: return
            updateStatusText(status)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        ipEditText = findViewById(R.id.editTextMacIp)
        toggleButton = findViewById(R.id.buttonToggleService)
        statusText = findViewById(R.id.textViewStatus)
        crashLogButton = findViewById(R.id.buttonViewCrashLog)
        crashLogText = findViewById(R.id.textViewCrashLog)
        localBroadcast = LocalBroadcastManager.getInstance(this)

        loadSavedIp()
        requestRequiredPermissions()

        toggleButton.setOnClickListener {
            if (serviceRunning) stopService() else startServiceIfValid()
        }

        crashLogButton.setOnClickListener { showCrashLog() }
        crashLogButton.setOnLongClickListener { clearCrashLog(); true }
    }

    private fun crashLogFile() = java.io.File(getExternalFilesDir(null), "dashphone_crash.log")

    private fun showCrashLog() {
        val logFile = crashLogFile()
        crashLogText.text = if (logFile.exists()) logFile.readText() else "No crash log yet."
    }

    private fun clearCrashLog() {
        crashLogFile().delete()
        crashLogText.text = "Cleared."
        Toast.makeText(this, "Crash log cleared", Toast.LENGTH_SHORT).show()
    }

    override fun onResume() {
        super.onResume()
        localBroadcast.registerReceiver(statusReceiver, IntentFilter(ACTION_STATUS_BROADCAST))
    }

    override fun onPause() {
        super.onPause()
        localBroadcast.unregisterReceiver(statusReceiver)
    }

    private fun startServiceIfValid() {
        val ip = ipEditText.text.toString().trim()
        if (ip.isEmpty()) {
            Toast.makeText(this, getString(R.string.error_ip_required), Toast.LENGTH_SHORT).show()
            return
        }

        saveIp(ip)

        val serviceIntent = Intent(this, CallService::class.java).apply {
            putExtra(CallService.EXTRA_MAC_IP, ip)
        }
        ContextCompat.startForegroundService(this, serviceIntent)
        serviceRunning = true
        updateToggleButton()
        updateStatusText(ConnectionStatus.RECONNECTING)
    }

    private fun stopService() {
        val stopIntent = Intent(this, CallService::class.java).apply {
            action = CallService.ACTION_STOP_SERVICE
        }
        startService(stopIntent)
        serviceRunning = false
        updateToggleButton()
        updateStatusText(ConnectionStatus.DISCONNECTED)
    }

    private fun updateToggleButton() {
        toggleButton.text = if (serviceRunning) {
            getString(R.string.button_stop)
        } else {
            getString(R.string.button_start)
        }
    }

    private fun updateStatusText(status: ConnectionStatus) {
        statusText.text = when (status) {
            ConnectionStatus.CONNECTED -> getString(R.string.status_connected)
            ConnectionStatus.DISCONNECTED -> getString(R.string.status_disconnected)
            ConnectionStatus.RECONNECTING -> getString(R.string.status_reconnecting)
        }
    }

    private fun loadSavedIp() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val savedIp = prefs.getString(PREF_MAC_IP, "")
        ipEditText.setText(savedIp)
    }

    private fun saveIp(ip: String) {
        getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(PREF_MAC_IP, ip)
            .apply()
    }

    private fun requestRequiredPermissions() {
        val required = mutableListOf(
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.READ_CALL_LOG,
            Manifest.permission.ANSWER_PHONE_CALLS
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            required.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val missing = required.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missing.toTypedArray(), REQUEST_PERMISSIONS)
        }
    }
}
