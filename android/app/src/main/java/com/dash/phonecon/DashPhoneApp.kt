package com.dash.phonecon

import android.app.Application
import android.util.Log
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private const val TAG = "DashPhoneApp"
private const val CRASH_LOG_FILE = "dashphone_crash.log"

class DashPhoneApp : Application() {

    override fun onCreate() {
        super.onCreate()
        installCrashHandler()
    }

    private fun installCrashHandler() {
        val previousHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            writeCrashLog(thread, throwable)
            previousHandler?.uncaughtException(thread, throwable)
        }
    }

    private fun writeCrashLog(thread: Thread, throwable: Throwable) {
        runCatching {
            val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
            val stackTrace = StringWriter().also { sw ->
                PrintWriter(sw).use { throwable.printStackTrace(it) }
            }.toString()

            val log = buildString {
                appendLine("=== CRASH at $timestamp ===")
                appendLine("Thread: ${thread.name}")
                appendLine("Exception: ${throwable.javaClass.name}: ${throwable.message}")
                appendLine()
                appendLine(stackTrace)
                appendLine()
            }

            val logFile = File(getExternalFilesDir(null), CRASH_LOG_FILE)
            logFile.appendText(log)
            Log.e(TAG, "Crash logged to ${logFile.absolutePath}")
        }
    }
}
