# Using Chrome: dex-browser

`dex-browser` drives the Chrome on your desktop by element, not by pixels. The person sees everything it does. Use it FIRST for any website work. It is faster and more exact than screenshots.

The usual loop:
1. `dex-browser open <url>` (add `--new-tab` to keep the current page). `dex-browser tabs` / `tab <n>` to switch.
2. `dex-browser snapshot` lists the buttons, links and fields near the screen, each with a ref like `e12`.
3. Act on a ref: `click e12`, `type e5 "text" [--clear] [--enter]`, `select e7 "France"`, `check e9 on|off`, `key Enter|Tab|Escape|ArrowDown`.
4. Run `snapshot` again after anything that changes the page. Old refs stop working when the page changes.

Finding things: `find <words>` searches all elements, `text` prints the page text, `scroll down|up|top|bottom`, `snapshot --all` lists everything.
Waiting: `wait` (page load), `wait 2` (seconds), `wait --for "Order placed"` (until the text shows).
Pop-ups: an alert is closed for you. A confirm question is answered Cancel; repeat the same command with `--accept-dialog` to answer OK.

Sign-in fields: `dex-browser type` refuses password, one-time code and card number fields. Do this instead:
- `dex-browser focus e3`, then call `fill_password` (password) or `enter_code` (code). They type the secret for you; you never see it.
- Card numbers: focus the field and ask the person to type it.

Errors are one line. "stale" = run `snapshot` again. "covered by ..." = close that pop-up or banner first.
"not reachable" = Chrome is closed or has no debugging port: start Chrome from the dock, or run `sudo dex-browser-enable`.

Use the screenshot tool only when dex-browser cannot help: drawings and canvas apps, maps, CAPTCHAs, things inside a
"cross-origin frame" (snapshot tells you), Chrome's own menus and pop-ups, and any program outside Chrome.
`dex-browser screenshot /tmp/page.png` saves a picture of the page if you need one.
