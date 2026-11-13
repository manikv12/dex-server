# A bot's desktop: clean Ubuntu (XFCE) with a dock at the bottom (Chrome,
# Terminal, Files, clock) and a wallpaper made from the bot's color.
# Built on the server by server/setup-desktops.sh as dexbot/desktop:1.
FROM kasmweb/core-ubuntu-noble:1.18.0-rolling-daily
USER root

RUN apt-get update \
 && apt-get install -y --no-install-recommends xfce4-terminal thunar wget ca-certificates fonts-inter python3-websockets xdotool sudo \
 && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
 && apt-get install -y /tmp/chrome.deb \
 && rm -f /tmp/chrome.deb && rm -rf /var/lib/apt/lists/*

# Chrome: English and US even though the server's owner (OVH) is French.
COPY chrome/dexbot.json /etc/opt/chrome/policies/managed/dexbot.json

# Chrome inside a container: no sandbox, no first-run screens, its own password store.
# DevTools port on localhost only, so the bot can drive Chrome by element (dex-browser).
# Chrome ignores that port on its default profile folder, so the profile is ~/.config/dex-chrome.
RUN for f in /usr/share/applications/google-chrome.desktop /usr/share/applications/com.google.Chrome.desktop; do \
      [ -f "$f" ] && sed -i 's#^Exec=/usr/bin/google-chrome-stable#Exec=/usr/bin/google-chrome-stable --no-sandbox --test-type --no-first-run --password-store=basic --start-maximized --lang=en-US --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir=/home/kasm-user/.config/dex-chrome#' "$f"; \
    done; true

# One misty wallpaper per bot color (server/desktop/wallpapers); the desktop
# shows the one for $BOT_COLOR_NAME (custom_startup.sh links it in at start).
COPY wallpapers/ /usr/share/backgrounds/dexbot/
RUN mkdir -p /usr/share/backgrounds && ln -sf /tmp/dexbot-wall.jpg /usr/share/backgrounds/bg_default.png

# A fresh bot home starts from this profile: the dock, no desktop icons.
COPY xfce4-panel.xml /home/kasm-default-profile/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml
COPY launchers/ /home/kasm-default-profile/.config/xfce4/panel/
RUN f=/home/kasm-default-profile/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml; \
    if [ -f "$f" ]; then sed -i 's#</channel>#  <property name="desktop-icons" type="empty"><property name="style" type="int" value="0"/></property>\n</channel>#' "$f"; fi; \
    rm -f /home/kasm-default-profile/Desktop/*.desktop; \
    chown -R 1000:1000 /home/kasm-default-profile

# A wide 1440x900 desktop that viewers can't shrink (the app scales it to fit).
RUN printf '\ndesktop:\n  resolution:\n    width: 1440\n    height: 900\n  allow_resize: false\n' >> /etc/kasmvnc/kasmvnc.yaml

# The relay: Chrome's traffic can go out through the person's iPhone or Mac (see dexbot-relay.py).
# The bot's hands (screen, mouse, keyboard, terminal) are served by the relay too.
COPY dexbot-relay.py /usr/local/bin/dexbot-relay
COPY dexbot_hands.py /usr/local/bin/dexbot_hands.py
# The bot's browser tool (Chrome by element over the DevTools port) and its short guide.
COPY dex-browser dex-browser-enable /usr/local/bin/
COPY BROWSER.md /usr/local/share/dexbot/BROWSER.md
COPY custom_startup.sh /dockerstartup/custom_startup.sh
RUN chmod 755 /dockerstartup/custom_startup.sh /usr/local/bin/dexbot-relay \
 && chmod 755 /usr/local/bin/dex-browser /usr/local/bin/dex-browser-enable \
 && chmod 644 /usr/local/bin/dexbot_hands.py /usr/local/share/dexbot/BROWSER.md

# The bot is the owner of its own computer: it may install things (root only
# inside this container, which can't reach the server or the other bots).
RUN echo 'kasm-user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/dexbot-bot && chmod 440 /etc/sudoers.d/dexbot-bot

USER 1000
