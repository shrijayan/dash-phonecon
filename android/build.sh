#!/bin/bash
set -e

export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH="$ANDROID_HOME/platform-tools:$PATH"

echo "Building DashPhone APK..."
./gradlew assembleDebug

APK="app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "Done: $APK"
echo ""
echo "Install on connected phone:"
echo "  adb install -r $APK"
