# Dex server

Your own server for the Dex app: the hub that runs your bots, and one small computer
(a desktop with Chrome) per bot. It runs on any provider's Linux server.

## What you need

- A server with Ubuntu 22.04 or 24.04, or Debian 12 or 13
- Intel/AMD (x86_64), 4 GB of memory or more, 20 GB of free disk
- Ports 80 and 443 free (Dex sets up HTTPS by itself; no domain name is needed)

Each bot's computer can use up to 2 GB of memory, so 4 GB is enough for about two bots.

## Install

Sign in to the server and run:

```bash
curl -fsSL https://github.com/manikv12/dex-server/releases/latest/download/install.sh | sudo bash
```

It takes a few minutes. At the end it shows a code, as text and as a QR code.

## Connect the app

In Dex, open **Settings › Cloud computer**, then scan the QR code (iPhone, iPad) or paste the
code (Mac). The code holds your server's key: give it only to your own devices.

To see the code again later:

```bash
sudo dexbot-connect-code | qrencode -t ANSIUTF8
```

## Update

Run the install command again. Your key, your bots and their files are kept.

## What is in this repository

- `install.sh`: the installer. Each release also has `dex-server.tar.gz`, which holds the hub
  and its setup steps.
- `desktop/`: what the bots' desktop image is built from (`ghcr.io/manikv12/dex-desktop`).
