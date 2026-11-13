#!/usr/bin/env python3
"""DexBot relay: lets a bot's Chrome use the person's iPhone (or Mac) internet.

Runs inside each bot's desktop container.
  - SOCKS5 on 127.0.0.1:1080. Chrome always uses it (managed policy).
  - WebSocket on 0.0.0.0:6902. The DexBot app connects here (through Caddy,
    which checks the access key) and carries the bot's connections.
    With ?role=hands it's the bot's hands instead (dexbot_hands.py).

Which internet the bot uses (~/.dexbot/route, set by the app):
  phone       connections go out from the person's device (DexBot open on it,
              with "Use This iPhone's Internet" on in Settings). With several
              devices, the one that connected last (opened last) carries them;
              the others wait and take over if it goes away. With no device
              connected they go out from the server, so tasks keep running
              while the phone is away (the app shows which).
  phone-only  the same, but with no device connected they fail ("Only This
              iPhone" in Settings).
  direct      connections go out from the server (the default).
The bot's own computer (localhost, 127.x, ::1) always goes direct, in every mode: through a device it
would mean the device's own localhost (for example a tool on the bot's computer at localhost:8080).

Frames on the WebSocket (binary): 1 byte type, 4 bytes stream id, payload.
  1 OPEN       relay -> app   payload "host:port"
  2 OPEN_OK    app -> relay
  3 OPEN_FAIL  app -> relay   payload: reason (utf-8)
  4 DATA       both ways
  5 CLOSE      both ways
  7 MODE       app -> relay   payload "phone" / "phone-only" (this device carries) or "direct" (turned off)
  8 STATUS     relay -> app   "use=active" / "use=standby" to carrying devices,
                              "mode=direct" after MODE direct (stream id 0)
  9 HELLO      app -> relay   payload JSON {"id", "name", "model"}: which device this is
 10 DEVICES    relay -> app   payload JSON [{"id", "name", "model", "state", "lastSeen"}]: every
                              device ever seen (live, standby or offline), to every
                              connected app whenever the list changes. The one list
                              all apps show (~/.dexbot/devices.json).
"""
import asyncio
import ipaddress
import json
import os
import socket
import struct
import sys
import time

import websockets

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import dexbot_hands  # noqa: E402  (the bot's own computer: screen, mouse, keyboard, terminal)

OPEN, OPEN_OK, OPEN_FAIL, DATA, CLOSE, MODE, STATUS, HELLO, DEVICES = 1, 2, 3, 4, 5, 7, 8, 9, 10
ROUTE_FILE = os.path.expanduser("~/.dexbot/route")
DEVICES_FILE = os.path.expanduser("~/.dexbot/devices.json")
CHUNK = 32 * 1024
GONE = "the device disconnected"


def read_mode():
    try:
        with open(ROUTE_FILE) as f:
            mode = f.read().strip()
            return mode if mode in ("phone", "phone-only") else "direct"
    except OSError:
        return "direct"


def write_mode(mode):
    os.makedirs(os.path.dirname(ROUTE_FILE), exist_ok=True)
    with open(ROUTE_FILE, "w") as f:
        f.write(mode)


def frame(kind, sid, payload=b""):
    return struct.pack(">BI", kind, sid) + payload


class Device:
    """One connected device and the connections it carries."""

    def __init__(self, ws):
        self.ws = ws
        self.info = {}           # from HELLO: id, name, model
        self.streams = {}        # sid -> asyncio.Queue of bytes (None = closed)
        self.opens = {}          # sid -> Future[str|None] (None = ok, str = error)

    async def send(self, kind, sid, payload=b""):
        await self.ws.send(frame(kind, sid, payload))

    def drop_all(self):
        for q in self.streams.values():
            q.put_nowait(None)
        for f in self.opens.values():
            if not f.done():
                f.set_result(GONE)
        self.streams.clear()
        self.opens.clear()


devices = []                     # oldest first; the last one carries the traffic


def load_known():
    try:
        with open(DEVICES_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


known = load_known()             # device id -> {"name", "model", "lastSeen"}: every device seen


def remember(info):
    if not info.get("id"):
        return
    known[info["id"]] = {"name": info.get("name", ""), "model": info.get("model", ""), "lastSeen": time.time()}
    try:
        os.makedirs(os.path.dirname(DEVICES_FILE), exist_ok=True)
        with open(DEVICES_FILE, "w") as f:
            json.dump(known, f)
    except OSError:
        pass
conns = set()                    # every app connection (carrying or only watching)
next_id = 1


async def announce():
    """Tells each device whether it carries the traffic now, and every app who's connected."""
    for d in list(devices):
        state = b"use=active" if d is devices[-1] else b"use=standby"
        try:
            await d.send(STATUS, 0, state)
        except Exception:
            pass
    now = time.time()
    rows = [dict(d.info, state="live" if d is devices[-1] else "standby", lastSeen=now) for d in devices]
    carrying = {r.get("id") for r in rows}
    online = {c.info.get("id") for c in conns if c.info.get("id")}
    for did, k in known.items():
        if did not in carrying:
            rows.append({"id": did, "name": k.get("name", ""), "model": k.get("model", ""),
                         # Connected but not carrying (its switch is off) still counts as seen now.
                         "state": "off" if did in online else "offline",
                         "lastSeen": now if did in online else k.get("lastSeen", 0)})
    listing = json.dumps(rows).encode()
    for c in list(conns):
        try:
            await c.send(DEVICES, 0, listing)
        except Exception:
            pass


async def app_handler(ws, path=None):
    path = path or getattr(ws, "path", None) or getattr(getattr(ws, "request", None), "path", "") or ""
    if "role=hands" in path:
        await dexbot_hands.serve(ws)
        return
    dev = Device(ws)                              # carries traffic once it sends MODE phone
    conns.add(dev)
    try:
        async for msg in ws:
            if not isinstance(msg, (bytes, bytearray)) or len(msg) < 5:
                continue
            kind, sid = struct.unpack(">BI", msg[:5])
            payload = bytes(msg[5:])
            if kind == MODE:
                if payload in (b"phone", b"phone-only"):
                    write_mode(payload.decode())
                    if dev not in devices:
                        devices.append(dev)
                else:
                    if dev in devices:
                        devices.remove(dev)
                    if not devices:                # other devices still on keep carrying
                        write_mode("direct")
                    await dev.send(STATUS, 0, b"mode=direct")
                await announce()
            elif kind == HELLO:
                try:
                    info = json.loads(payload)
                    dev.info = {k: str(info.get(k, ""))[:60] for k in ("id", "name", "model")}
                    remember(dev.info)
                except ValueError:
                    pass
                await announce()
            elif kind in (OPEN_OK, OPEN_FAIL):
                f = dev.opens.pop(sid, None)
                if f and not f.done():
                    f.set_result(None if kind == OPEN_OK else payload.decode(errors="replace") or "failed")
            elif kind == DATA:
                q = dev.streams.get(sid)
                if q:
                    q.put_nowait(payload)
            elif kind == CLOSE:
                q = dev.streams.pop(sid, None)
                if q:
                    q.put_nowait(None)
    finally:
        conns.discard(dev)
        if dev.info.get("id"):
            remember(dev.info)                    # last seen: now
            await announce()
        if dev in devices:
            devices.remove(dev)
            await announce()
        dev.drop_all()


# ---- SOCKS5 -------------------------------------------------------------

async def socks_reply(writer, code):
    writer.write(b"\x05" + bytes([code]) + b"\x00\x01" + b"\x00" * 6)
    await writer.drain()


async def read_target(reader, writer):
    head = await reader.readexactly(2)
    if head[0] != 5:
        return None
    await reader.readexactly(head[1])
    writer.write(b"\x05\x00")                     # no authentication
    await writer.drain()
    ver, cmd, _, atyp = await reader.readexactly(4)
    if atyp == 1:
        host = socket.inet_ntop(socket.AF_INET, await reader.readexactly(4))
    elif atyp == 3:
        host = (await reader.readexactly((await reader.readexactly(1))[0])).decode()
    elif atyp == 4:
        host = socket.inet_ntop(socket.AF_INET6, await reader.readexactly(16))
    else:
        return None
    port = struct.unpack(">H", await reader.readexactly(2))[0]
    if cmd != 1:                                  # CONNECT only
        await socks_reply(writer, 7)
        return None
    return host, port


async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(CHUNK)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def direct(host, port, reader, writer):
    try:
        r2, w2 = await asyncio.wait_for(asyncio.open_connection(host, port), 15)
    except Exception:
        await socks_reply(writer, 5)
        writer.close()
        return
    await socks_reply(writer, 0)
    await asyncio.gather(pipe(reader, w2), pipe(r2, writer))


async def open_on(dev, host, port):
    """Asks a device to open host:port. Returns (sid, None) or (None, error)."""
    global next_id
    sid = next_id
    next_id = next_id % 0xFFFFFFF0 + 1
    dev.streams[sid] = asyncio.Queue()
    opened = asyncio.get_running_loop().create_future()
    dev.opens[sid] = opened
    try:
        await dev.send(OPEN, sid, f"{host}:{port}".encode())
    except Exception:
        err = GONE                                # its connection just closed
    else:
        try:
            err = await asyncio.wait_for(opened, 20)
        except asyncio.TimeoutError:
            err = "no answer"
    if err is not None:
        dev.streams.pop(sid, None)
        dev.opens.pop(sid, None)
        return None, err
    return sid, None


async def via_device(dev, sid, reader, writer):
    q = dev.streams[sid]

    async def up():
        try:
            while True:
                data = await reader.read(CHUNK)
                if not data:
                    break
                await dev.send(DATA, sid, data)
        except Exception:
            pass
        finally:
            if dev.streams.pop(sid, None) is not None:
                try:
                    await dev.send(CLOSE, sid)
                except Exception:
                    pass
            q.put_nowait(None)

    async def down():
        try:
            while True:
                data = await q.get()
                if data is None:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    await asyncio.gather(up(), down())


def is_loopback(host):
    """localhost on the bot's own computer (never something a device can reach for it)."""
    h = host.strip("[]").lower().rstrip(".")
    if h == "localhost" or h.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


async def socks_handler(reader, writer):
    try:
        target = await read_target(reader, writer)
        if not target:
            writer.close()
            return
        host, port = target
        if is_loopback(host):                     # the bot's own computer: never through a device
            await direct(host, port, reader, writer)
            return
        # The newest device; if it went away meanwhile, the next one.
        while devices:
            dev = devices[-1]
            sid, err = await open_on(dev, host, port)
            if sid is not None:
                await socks_reply(writer, 0)
                await via_device(dev, sid, reader, writer)
                return
            if err != GONE:                       # the device refused or couldn't reach it
                await socks_reply(writer, 5)
                writer.close()
                return
            if dev in devices:
                devices.remove(dev)
        if read_mode() == "phone-only":
            await socks_reply(writer, 1)          # "Only This iPhone": fail rather than use the server
            writer.close()
            return
        await direct(host, port, reader, writer)
    except (asyncio.IncompleteReadError, ConnectionError):
        writer.close()


async def main():
    await asyncio.start_server(socks_handler, "127.0.0.1", 1080)
    # Short pings: a device that went to sleep is noticed within ~20 s.
    async with websockets.serve(app_handler, "0.0.0.0", 6902, max_size=2**22, ping_interval=10, ping_timeout=10):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
