#!/usr/bin/env bash
# Runs inside the bot's desktop session (Kasm restarts it if it ends, so it stays).
# Wallpaper: the misty one in the bot's color ($BOT_COLOR_NAME: pink, teal, ...).
NAME="${BOT_COLOR_NAME:-violet}"
WALL="/usr/share/backgrounds/dexbot/${NAME}.jpg"
[ -f "$WALL" ] || WALL=/usr/share/backgrounds/dexbot/violet.jpg
ln -sf "$WALL" /tmp/dexbot-wall.jpg

# Desktop size: 1440x900 (KasmVNC starts at 1024x768 otherwise).
for _ in $(seq 1 20); do xrandr >/dev/null 2>&1 && break; sleep 0.5; done
xrandr --fb 1440x900 >/dev/null 2>&1 || true

# The relay (Chrome's proxy; can send traffic through the person's device). Restarts if it stops.
(while true; do python3 /usr/local/bin/dexbot-relay >>/tmp/dexbot-relay.log 2>&1; sleep 1; done &)

# Chrome's profile is ~/.config/dex-chrome (Chrome refuses its DevTools port on the default
# folder). Homes from before: move the old profile over once, so sign-ins are kept.
if [ -d "$HOME/.config/google-chrome" ] && [ ! -e "$HOME/.config/dex-chrome" ] \
   && ! pgrep -u "$(id -u)" -f /opt/google/chrome/chrome >/dev/null; then
  mv "$HOME/.config/google-chrome" "$HOME/.config/dex-chrome"
fi

# A restart leaves Chrome's "in use" lock from the old session: clear it.
rm -f "$HOME/.config/dex-chrome/Singleton"* "$HOME/.config/google-chrome/Singleton"* 2>/dev/null

# Show it once the desktop is up.
for _ in $(seq 1 30); do pgrep -x xfdesktop >/dev/null && break; sleep 1; done
xfdesktop --reload >/dev/null 2>&1 || true

# The dock: our layout for homes made before it existed.
if ! grep -q 'dexbot-dock' "$HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml" 2>/dev/null; then
  mkdir -p "$HOME/.config/xfce4/xfconf/xfce-perchannel-xml" "$HOME/.config/xfce4/panel"
  cp /home/kasm-default-profile/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml "$HOME/.config/xfce4/xfconf/xfce-perchannel-xml/"
  cp -r /home/kasm-default-profile/.config/xfce4/panel/. "$HOME/.config/xfce4/panel/"
  xfce4-panel --quit >/dev/null 2>&1; pkill -x xfconfd; sleep 1
  (xfce4-panel >/dev/null 2>&1 &)
fi
# Dock launchers: always the image's current ones (Chrome's flags can change).
cp -r /home/kasm-default-profile/.config/xfce4/panel/. "$HOME/.config/xfce4/panel/" 2>/dev/null

exec sleep infinity
