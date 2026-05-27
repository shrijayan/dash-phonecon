package com.dash.phonecon

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.util.Log
import androidx.core.content.ContextCompat

private const val TAG = "BootReceiver"
private const val PREFS_NAME = "dash_phonecon_prefs"
private const val PREF_MAC_IP = "mac_ip"

class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return

        val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val macIp = prefs.getString(PREF_MAC_IP, null)

        if (macIp.isNullOrBlank()) {
            Log.w(TAG, "No mac_ip saved — skipping auto-start after boot")
            return
        }

        Log.d(TAG, "Boot completed — starting CallService with ip=$macIp")
        val serviceIntent = Intent(context, CallService::class.java).apply {
            putExtra(CallService.EXTRA_MAC_IP, macIp)
        }
        ContextCompat.startForegroundService(context, serviceIntent)
    }
}
