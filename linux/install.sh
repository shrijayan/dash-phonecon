#!/bin/bash
# One-line installer for Dash Phone Con on Ubuntu/Debian-based systems.
#
# Downloads the latest .deb from GitHub Releases and installs it with apt,
# so all package dependencies (PySide6, websockets, ...) are resolved
# automatically - no manual `apt install python3-...` steps, no cloning the
# repo, no build tools required.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/shrijayan/dash-phonecon/main/linux/install.sh | bash
#
# Or, to install a specific version instead of the latest:
#   curl -fsSL .../install.sh | bash -s -- --version 1.2.0
set -euo pipefail

REPO="shrijayan/dash-phonecon"
VERSION="latest"

while [ $# -gt 0 ]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ "$(id -u)" -eq 0 ]; then
  echo "Don't run this installer as root - it calls sudo itself where needed." >&2
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer needs apt (Debian/Ubuntu). For other distros, see:" >&2
  echo "  https://github.com/${REPO}#install" >&2
  exit 1
fi

ARCH="$(dpkg --print-architecture 2>/dev/null || echo all)"
if [ "$ARCH" != "amd64" ] && [ "$ARCH" != "all" ]; then
  echo "Note: this package is architecture 'all' (pure Python) so it should" >&2
  echo "still work on ${ARCH}, but it has only been tested on amd64." >&2
fi

echo "==> Resolving release..."
if [ "$VERSION" = "latest" ]; then
  API_URL="https://api.github.com/repos/${REPO}/releases/latest"
else
  API_URL="https://api.github.com/repos/${REPO}/releases/tags/v${VERSION}"
fi

RELEASE_JSON="$(curl -fsSL "$API_URL")" || {
  echo "Could not reach GitHub's API to look up the release. Check your network and try again." >&2
  exit 1
}

DEB_URL="$(printf '%s' "$RELEASE_JSON" | grep -o '"browser_download_url": *"[^"]*\.deb"' | head -1 | sed -E 's/.*"(https:[^"]+)"/\1/')"
TAG_NAME="$(printf '%s' "$RELEASE_JSON" | grep -o '"tag_name": *"[^"]*"' | head -1 | sed -E 's/.*"(v[^"]+)"/\1/')"

if [ -z "$DEB_URL" ]; then
  echo "Could not find a .deb asset on release ${VERSION}. See releases:" >&2
  echo "  https://github.com/${REPO}/releases" >&2
  exit 1
fi

echo "==> Found ${TAG_NAME:-$VERSION}"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

DEB_FILE="${WORKDIR}/$(basename "$DEB_URL")"
echo "==> Downloading $(basename "$DEB_URL")..."
curl -fsSL -o "$DEB_FILE" "$DEB_URL"

SHA_URL="${DEB_URL}.sha256"
if curl -fsSL -o "${DEB_FILE}.sha256" "$SHA_URL" 2>/dev/null; then
  echo "==> Verifying checksum..."
  (cd "$WORKDIR" && sha256sum -c "$(basename "$DEB_FILE").sha256") || {
    echo "Checksum verification failed - aborting install." >&2
    exit 1
  }
fi

echo "==> Installing (you may be asked for your sudo password)..."
sudo apt-get install -y "$DEB_FILE"

echo ""
echo "Done! Dash Phone Con ${TAG_NAME:-} is installed."
echo ""
echo "Start it now (or log out/in - it also autostarts):"
echo "  dash-phonecon &"
echo ""
echo "Next: install the companion Android app on your phone and point it at"
echo "this computer's IP - see https://${REPO%%/*}.github.io/${REPO#*/}/docs/ubuntu/first-run"
