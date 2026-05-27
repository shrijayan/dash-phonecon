#!/bin/bash
set -e

PRODUCT="DashPhone"
APP_BUNDLE="build/${PRODUCT}.app"
CONTENTS="${APP_BUNDLE}/Contents"

echo "Building ${PRODUCT}..."
swift build -c release

echo "Bundling ${PRODUCT}.app..."
rm -rf "${APP_BUNDLE}"
mkdir -p "${CONTENTS}/MacOS" "${CONTENTS}/Resources"

cp ".build/release/${PRODUCT}" "${CONTENTS}/MacOS/${PRODUCT}"
cp "${PRODUCT}/Info.plist"     "${CONTENTS}/Info.plist"

echo "Signing..."
codesign --force --deep \
    --entitlements "${PRODUCT}/DashPhone.entitlements" \
    --sign - \
    "${APP_BUNDLE}"

echo ""
echo "Done: ${APP_BUNDLE}"
echo "Run: open ${APP_BUNDLE}"
