#!/bin/bash
# Builds a binary .deb for Dash Phone Con from the source in src/dashphone.
# Produces dist/dash-phonecon_<version>_all.deb.
#
# This is a "flat" binary .deb (hand-assembled with dpkg-deb), the same
# technique many small desktop tools use to ship a real, apt-installable
# package without the full Debian source-packaging machinery (changelogs,
# orig tarballs, lintian-clean policy, ...) meant for archive uploads.
#
# Usage:
#   ./build-deb.sh
#   sudo apt install ./dist/dash-phonecon_*_all.deb

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PACKAGE_NAME="dash-phonecon"
VERSION="$(grep -oP '__version__\s*=\s*"\K[^"]+' src/dashphone/__init__.py)"
ARCH="all"
STAGING_DIR="dist/pkgroot"
DEB_FILE="dist/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "Building ${PACKAGE_NAME} ${VERSION}..."

rm -rf "${STAGING_DIR}" "${DEB_FILE}"
mkdir -p \
    "${STAGING_DIR}/DEBIAN" \
    "${STAGING_DIR}/usr/lib/python3/dist-packages" \
    "${STAGING_DIR}/usr/bin" \
    "${STAGING_DIR}/usr/share/applications" \
    "${STAGING_DIR}/etc/xdg/autostart" \
    "${STAGING_DIR}/usr/share/icons/hicolor/256x256/apps" \
    "${STAGING_DIR}/usr/share/doc/${PACKAGE_NAME}"

echo "Copying application source..."
cp -r src/dashphone "${STAGING_DIR}/usr/lib/python3/dist-packages/"
find "${STAGING_DIR}/usr/lib/python3/dist-packages/dashphone" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "Installing launcher..."
install -m 755 packaging/dash-phonecon "${STAGING_DIR}/usr/bin/dash-phonecon"

echo "Installing desktop entry (app menu + autostart)..."
install -m 644 packaging/dash-phonecon.desktop "${STAGING_DIR}/usr/share/applications/dash-phonecon.desktop"
install -m 644 packaging/dash-phonecon.desktop "${STAGING_DIR}/etc/xdg/autostart/dash-phonecon.desktop"

echo "Rendering app icon (reuses the same drawing code as the tray icon)..."
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 packaging/render_icon.py \
    "${STAGING_DIR}/usr/share/icons/hicolor/256x256/apps/dash-phonecon.png"

echo "Writing control file (version ${VERSION})..."
sed "s/__VERSION__/${VERSION}/" packaging/control.in > "${STAGING_DIR}/DEBIAN/control"
install -m 755 packaging/postinst "${STAGING_DIR}/DEBIAN/postinst"
install -m 755 packaging/postrm "${STAGING_DIR}/DEBIAN/postrm"

echo "Copying docs..."
cp README.md "${STAGING_DIR}/usr/share/doc/${PACKAGE_NAME}/README.md"

echo "Normalising permissions (independent of the umask of whoever runs this script)..."
find "${STAGING_DIR}" -type d -exec chmod 755 {} +
find "${STAGING_DIR}" -type f -exec chmod 644 {} +
chmod 755 \
    "${STAGING_DIR}/usr/bin/dash-phonecon" \
    "${STAGING_DIR}/DEBIAN/postinst" \
    "${STAGING_DIR}/DEBIAN/postrm"

echo "Building .deb..."
mkdir -p dist
dpkg-deb --build --root-owner-group "${STAGING_DIR}" "${DEB_FILE}"

echo ""
echo "Done: ${DEB_FILE}"
echo "Install with: sudo apt install ./${DEB_FILE}"
echo "Remove with:  sudo apt remove ${PACKAGE_NAME}"
