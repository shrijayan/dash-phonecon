package com.dash.phonecon

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager
import android.util.Log

private const val TAG = "PhoneStateReceiver"

interface CallEventListener {
    fun onRinging(number: String, contactName: String?)
    fun onCallActive()
    fun onCallEnded()
}

class PhoneStateReceiver(private val listener: CallEventListener) : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return

        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE) ?: return
        Log.d(TAG, "Phone state changed: $state")

        when (state) {
            TelephonyManager.EXTRA_STATE_RINGING -> {
                val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER) ?: ""
                val contactName = if (number.isNotEmpty()) ContactHelper.lookupName(context, number) else null
                listener.onRinging(number, contactName)
            }
            TelephonyManager.EXTRA_STATE_OFFHOOK -> listener.onCallActive()
            TelephonyManager.EXTRA_STATE_IDLE -> listener.onCallEnded()
        }
    }
}
