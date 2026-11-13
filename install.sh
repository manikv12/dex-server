#!/usr/bin/env bash
# Dex server: one command on a fresh server, from any provider.
#
#   curl -fsSL https://github.com/OWNER/dex-server/releases/latest/download/install.sh | sudo bash
#
# It needs: Ubuntu 22.04 / 24.04 or Debian 12 / 13, an Intel/AMD (x86_64) machine, 4 GB of memory,
# 20 GB of free disk, and ports 80 and 443 free. It installs Docker, Caddy (HTTPS), the Dex hub and
# the bots' ready-made desktop image, then shows the code the Dex app asks for (as text and as a QR
# code). Nothing is built on the server. Safe to run again: it updates what is there and keeps the
# key, the bots and their files.
#
# Settings (all optional): DEX_REPO (where releases are), DEX_VERSION (a release tag; default: the latest).
set -euo pipefail

REPO="${DEX_REPO:-manikv12/dex-server}"
VERSION="${DEX_VERSION:-latest}"

say()  { printf '\n== %s\n' "$*"; }
fail() { printf '\nDex was not installed: %s\n' "$*" >&2; exit 1; }

# ---- Checks first: nothing is changed on a server that can't run it ----
[ "$(id -u)" = 0 ] || fail "run this as root (put sudo in front of bash)."
[ "$(uname -m)" = x86_64 ] || fail "this server is $(uname -m). Dex needs an Intel/AMD (x86_64) server for now."
[ -r /etc/os-release ] || fail "this doesn't look like Ubuntu or Debian."
. /etc/os-release
case "${ID:-}:${VERSION_ID:-}" in
  ubuntu:22.04|ubuntu:24.04|debian:12|debian:13) ;;
  *) fail "this is ${PRETTY_NAME:-an unknown system}. Use Ubuntu 22.04 or 24.04, or Debian 12 or 13." ;;
esac
mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
[ "$mem_mb" -ge 3500 ] || fail "this server has ${mem_mb} MB of memory. Dex needs 4 GB (each bot's computer uses up to 2 GB)."
mkdir -p /data
free_gb=$(df -BG --output=avail /data | tail -1 | tr -dc 0-9)
[ "$free_gb" -ge 20 ] || fail "only ${free_gb} GB of disk is free. Dex needs 20 GB."
if ! command -v caddy >/dev/null; then
  for port in 80 443; do
    if ss -ltn 2>/dev/null | grep -q ":$port "; then
      fail "something already uses port $port on this server (a web server?). Dex needs ports 80 and 443 for itself."
    fi
  done
fi

export DEBIAN_FRONTEND=noninteractive
say "Getting ready"
apt-get update -y -q >/dev/null
apt-get install -y -q sudo curl ca-certificates tar openssl iproute2 qrencode >/dev/null

# ---- The release: the hub's files, the setup steps and the ready-made brain ----
say "Downloading Dex ($VERSION)"
if [ "$VERSION" = latest ]; then base="https://github.com/$REPO/releases/latest/download"
else base="https://github.com/$REPO/releases/download/$VERSION"; fi
work=$(mktemp -d)
curl -fsSL "$base/dex-server.tar.gz" -o "$work/dex-server.tar.gz" || fail "the download failed ($base). Check the server's internet connection."
curl -fsSL "$base/dex-server.tar.gz.sha256" -o "$work/sum" || fail "the download's check file is missing."
echo "$(awk '{print $1}' "$work/sum")  $work/dex-server.tar.gz" | sha256sum -c - >/dev/null || fail "the download is damaged. Run the command again."
rm -rf /tmp/dexbot-src /tmp/dexbot-desktop
mkdir -p /tmp/dexbot-src
tar xzf "$work/dex-server.tar.gz" -C /tmp/dexbot-src
rm -rf "$work"
cp -r /tmp/dexbot-src/server/desktop /tmp/dexbot-desktop
release=$(cat /tmp/dexbot-src/VERSION)

# ---- The same three steps as on our own server, with everything ready-made ----
mkdir -p /data/bots /data/shared
chown 1000:1000 /data/shared
export DEX_KEEP_SSH=1                                   # the owner's SSH setup is not touched
export DEX_DESKTOP_IMAGE="$(cat /tmp/dexbot-src/DESKTOP_IMAGE)"
say "Step 1 of 3: the server (updates, firewall, Docker)"
bash /tmp/dexbot-src/server/setup-base.sh
say "Step 2 of 3: the bots' computers (HTTPS, the desktop image)"
bash /tmp/dexbot-src/server/setup-desktops.sh
say "Step 3 of 3: the hub"
bash /tmp/dexbot-src/server/setup-hub.sh
echo "$release" > /etc/dexbot/version
rm -rf /tmp/dexbot-src /tmp/dexbot-desktop

# ---- The code for the app ----
code=$(/usr/local/bin/dexbot-connect-code)
say "Dex $release is ready"
echo "In the Dex app: Settings > Cloud computer > Connect your server. Scan this code, or paste the line under it."
echo "It holds this server's key: give it only to your own devices."
echo
qrencode -t ANSIUTF8 -m 2 "$code" || true
echo
echo "$code"
echo
echo "To see it again later:  sudo dexbot-connect-code | qrencode -t ANSIUTF8"
