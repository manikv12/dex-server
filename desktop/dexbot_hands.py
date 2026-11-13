"""DexBot hands: lets the bot use its own Linux computer.

Served by dexbot-relay on the same WebSocket port, at /_dexbot/relay?role=hands
(Caddy lets in only requests with the access key). JSON messages, one reply per
request, matched by "id":

  {"id":1, "op":"screen"}
      -> {"id":1, "ok":true, "width":1440, "height":900, "jpeg":"<base64>"}
  {"id":2, "op":"act", "actions":[...], "screen":true}
      -> {"id":2, "ok":true, ...screen fields when "screen" is true}
     actions (coordinates are desktop pixels, as in the screenshot):
       {"type":"click", "x":..,"y":.., "button":"left|right|middle"}
       {"type":"double_click", "x":..,"y":..}
       {"type":"move", "x":..,"y":..}
       {"type":"drag", "path":[{"x":..,"y":..}, ...]}
       {"type":"scroll", "x":..,"y":.., "scroll_x":0, "scroll_y":3}   (+ = down/right, in wheel steps)
       {"type":"type", "text":"..."}
       {"type":"key", "keys":["ctrl","l"]}                            (pressed together)
       {"type":"wait", "ms":1000}
  {"id":3, "op":"run", "command":"ls -la", "timeout":60}
      -> {"id":3, "ok":true, "exit":0, "output":"...", "truncated":false, "timed_out":false}

Input goes through the X server (xdotool), like a real mouse and keyboard:
curved, eased pointer moves, human pauses between presses, and typing at a
person's speed. Text (it may be a password the app filled) is never logged.
"""
import asyncio
import base64
import json
import math
import os
import random

DISPLAY = os.environ.get("DISPLAY", ":1")
ENV = dict(os.environ, DISPLAY=DISPLAY)
MAX_OUTPUT = 20000
KEYS = {
    "enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape", "tab": "Tab",
    "space": "space", "backspace": "BackSpace", "delete": "Delete", "del": "Delete",
    "up": "Up", "arrowup": "Up", "down": "Down", "arrowdown": "Down", "left": "Left", "arrowleft": "Left",
    "right": "Right", "arrowright": "Right", "home": "Home", "end": "End",
    "pageup": "Prior", "page_up": "Prior", "pagedown": "Next", "page_down": "Next",
    "ctrl": "ctrl", "control": "ctrl", "alt": "alt", "option": "alt", "shift": "shift",
    "cmd": "super", "command": "super", "meta": "super", "super": "super", "win": "super",
    "insert": "Insert", "capslock": "Caps_Lock", "printscreen": "Print",
}


async def sh(*args, stdin=None, timeout=30):
    p = await asyncio.create_subprocess_exec(*args, env=ENV, stdin=asyncio.subprocess.PIPE if stdin else None,
                                             stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await asyncio.wait_for(p.communicate(stdin), timeout)
    if p.returncode != 0:
        raise RuntimeError((err or out).decode(errors="replace").strip()[:300] or f"{args[0]} failed")
    return out


async def xdo(*args):
    await sh("xdotool", *[str(a) for a in args])


async def screen_size():
    out = await sh("xdotool", "getdisplaygeometry")
    w, h = out.decode().split()
    return int(w), int(h)


async def screenshot():
    w, h = await screen_size()
    jpeg = await sh("ffmpeg", "-loglevel", "error", "-f", "x11grab", "-video_size", f"{w}x{h}", "-i", DISPLAY,
                    "-frames:v", "1", "-f", "image2", "-c:v", "mjpeg", "-q:v", "4", "pipe:1")
    return {"width": w, "height": h, "jpeg": base64.b64encode(jpeg).decode()}


async def pointer():
    out = (await sh("xdotool", "getmouselocation", "--shell")).decode()
    vals = dict(line.split("=", 1) for line in out.split() if "=" in line)
    return int(vals.get("X", 0)), int(vals.get("Y", 0))


def ease(t):
    return t * t * (3 - 2 * t)


async def glide(x, y, slow=False):
    """Moves the pointer to (x, y) along a gentle curve, faster in the middle."""
    x0, y0 = await pointer()
    dist = math.hypot(x - x0, y - y0)
    if dist < 2:
        return
    # A bend to one side, a bit of the distance; two control points.
    nx, ny = -(y - y0) / dist, (x - x0) / dist
    bend = random.uniform(-0.18, 0.18) * dist
    c1 = (x0 + (x - x0) * 0.3 + nx * bend, y0 + (y - y0) * 0.3 + ny * bend)
    c2 = (x0 + (x - x0) * 0.7 + nx * bend * 0.6, y0 + (y - y0) * 0.7 + ny * bend * 0.6)
    steps = int(min(42, max(8, dist / 14)))
    total = min(0.75, max(0.16, 0.12 + dist * 0.00035)) * (1.8 if slow else 1)
    args, last = [], 0.0
    for i in range(1, steps + 1):
        t = ease(i / steps)
        px = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t ** 2 * c2[0] + t ** 3 * x
        py = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t ** 2 * c2[1] + t ** 3 * y
        if i == steps:
            px, py = x, y
        args += ["mousemove", str(int(round(px))), str(int(round(py))), "sleep", f"{total / steps:.3f}"]
        last = t
    await xdo(*args)


def pause(lo=0.04, hi=0.11):
    return f"{random.uniform(lo, hi):.3f}"


async def click(x, y, button="left", count=1):
    b = {"left": 1, "middle": 2, "right": 3}.get(button, 1)
    await glide(x, y)
    await asyncio.sleep(random.uniform(0.04, 0.12))
    args = []
    for i in range(count):
        if i:
            args += ["sleep", pause(0.07, 0.12)]
        args += ["mousedown", b, "sleep", pause(0.05, 0.11), "mouseup", b]
    await xdo(*args)


async def type_text(text):
    """Types at a person's speed: short bursts with small, uneven pauses."""
    i = 0
    fast = len(text) > 160
    while i < len(text):
        n = random.randint(2, 7) if not fast else random.randint(8, 20)
        chunk = text[i:i + n]
        i += n
        delay = random.randint(18, 45) if fast else random.randint(35, 110)
        await sh("xdotool", "type", "--delay", str(delay), "--", chunk)
        if not fast and random.random() < 0.15:
            await asyncio.sleep(random.uniform(0.12, 0.35))


def key_name(k):
    k = str(k).strip()
    low = k.lower()
    if low in KEYS:
        return KEYS[low]
    if len(low) in (2, 3) and low[0] == "f" and low[1:].isdigit():
        return k.upper()
    return k if len(k) > 1 else low


async def act(action):
    t = action.get("type")
    x, y = action.get("x"), action.get("y")
    if t in ("click", "double_click", "move", "scroll") and (x is None or y is None):
        raise ValueError(f"{t} needs x and y")
    if t == "click":
        await click(int(x), int(y), action.get("button") or "left")
    elif t == "double_click":
        await click(int(x), int(y), "left", 2)
    elif t == "move":
        await glide(int(x), int(y))
    elif t == "drag":
        path = action.get("path") or []
        if len(path) < 2:
            raise ValueError("drag needs a path of at least 2 points")
        await glide(int(path[0]["x"]), int(path[0]["y"]))
        await xdo("mousedown", 1, "sleep", pause(0.08, 0.15))
        for p in path[1:]:
            await glide(int(p["x"]), int(p["y"]), slow=True)
        await xdo("sleep", pause(0.06, 0.12), "mouseup", 1)
    elif t == "scroll":
        await glide(int(x), int(y))
        for amount, neg, pos in ((int(action.get("scroll_y") or 0), 4, 5), (int(action.get("scroll_x") or 0), 6, 7)):
            if amount:
                await xdo("click", "--repeat", min(abs(amount), 30), "--delay", random.randint(45, 90), pos if amount > 0 else neg)
    elif t == "type":
        await type_text(str(action.get("text") or ""))
    elif t == "key":
        keys = action.get("keys") or []
        if isinstance(keys, str):
            keys = [keys]
        if not keys:
            raise ValueError("key needs keys")
        await xdo("key", "--clearmodifiers", "+".join(key_name(k) for k in keys))
    elif t == "wait":
        await asyncio.sleep(min(float(action.get("ms") or 1000), 10000) / 1000)
    else:
        raise ValueError(f"unknown action {t!r}")


async def run(command, timeout):
    p = await asyncio.create_subprocess_exec("bash", "-lc", command, env=dict(ENV, TERM="dumb"),
                                             cwd=os.path.expanduser("~"), stdin=asyncio.subprocess.DEVNULL,
                                             stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                                             start_new_session=True)
    timed_out = False
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        timed_out = True
        try:
            os.killpg(p.pid, 9)
        except ProcessLookupError:
            pass
        out = b""
        try:
            out, _ = await asyncio.wait_for(p.communicate(), 3)
        except Exception:
            pass
    text = (out or b"").decode(errors="replace")
    truncated = len(text) > MAX_OUTPUT
    if truncated:                                  # keep the start and the end
        text = text[:MAX_OUTPUT // 2] + "\n…(cut)…\n" + text[-MAX_OUTPUT // 2:]
    return {"exit": p.returncode, "output": text, "truncated": truncated, "timed_out": timed_out}


async def handle(msg):
    op = msg.get("op")
    if op == "screen":
        return await screenshot()
    if op == "act":
        for a in msg.get("actions") or []:
            await act(a)
        if msg.get("screen"):
            await asyncio.sleep(0.6)               # let the screen settle
            return await screenshot()
        return {}
    if op == "run":
        timeout = max(1, min(float(msg.get("timeout") or 60), 600))
        return await run(str(msg.get("command") or ""), timeout)
    raise ValueError(f"unknown op {op!r}")


async def serve(ws):
    lock = asyncio.Lock()                          # one input sequence at a time

    async def one(raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        rid = msg.get("id")
        try:
            if msg.get("op") == "run":             # commands may run alongside screen work
                result = await handle(msg)
            else:
                async with lock:
                    result = await handle(msg)
            reply = {"id": rid, "ok": True, **result}
        except Exception as e:                      # the message never includes typed text
            reply = {"id": rid, "ok": False, "error": str(e)[:300]}
        try:
            await ws.send(json.dumps(reply))
        except Exception:
            pass

    tasks = set()
    async for raw in ws:
        if isinstance(raw, str):
            t = asyncio.create_task(one(raw))
            tasks.add(t)
            t.add_done_callback(tasks.discard)
