// Dex Passkeys: this bot's Chrome hands every passkey request (WebAuthn) to the person's own
// device. Chrome gives the request with the page's real address; the answer is one signed reply
// for that one request. Nothing is stored here.
const HOST = "ai.dex.passkeys";
const NOT_ALLOWED = { name: "NotAllowedError", message: "The passkey request was not approved." };
const open = new Map();                       // requestId -> the helper's port (to cancel)

function ask(msg) {
  return new Promise((resolve) => {
    let port, done = false;
    try {
      port = chrome.runtime.connectNative(HOST);
    } catch (e) {
      return resolve({ error: NOT_ALLOWED });
    }
    if (msg.id !== undefined) open.set(msg.id, port);
    const finish = (answer) => {
      if (done) return;
      done = true;
      if (msg.id !== undefined) open.delete(msg.id);
      resolve(answer);
    };
    port.onMessage.addListener((m) => { finish(m || {}); try { port.disconnect(); } catch (e) {} });
    port.onDisconnect.addListener(() => { void chrome.runtime.lastError; finish({ error: NOT_ALLOWED }); });
    port.postMessage(msg);
  });
}

function details(id, answer) {
  return typeof answer.response === "string"
    ? { requestId: id, responseJson: answer.response }
    : { requestId: id, error: (answer.error && answer.error.name) ? answer.error : NOT_ALLOWED };
}

chrome.webAuthenticationProxy.onGetRequest.addListener(async (r) => {
  const answer = await ask({ kind: "get", id: r.requestId, options: r.requestDetailsJson });
  if (answer.canceled) return;
  chrome.webAuthenticationProxy.completeGetRequest(details(r.requestId, answer)).catch(() => {});
});

chrome.webAuthenticationProxy.onCreateRequest.addListener(async (r) => {
  const answer = await ask({ kind: "create", id: r.requestId, options: r.requestDetailsJson });
  if (answer.canceled) return;
  chrome.webAuthenticationProxy.completeCreateRequest(details(r.requestId, answer)).catch(() => {});
});

// "Can this computer do passkeys?": yes only while one of the person's devices can approve them.
chrome.webAuthenticationProxy.onIsUvpaaRequest.addListener(async (r) => {
  const answer = await ask({ kind: "uvpaa" });
  chrome.webAuthenticationProxy.completeIsUvpaaRequest({ requestId: r.requestId, isUvpaa: answer.isUvpaa === true }).catch(() => {});
});

// The page gave up (or timed out): close the helper, which takes the question off the person's screen.
chrome.webAuthenticationProxy.onRequestCanceled.addListener((id) => {
  const port = open.get(id);
  if (!port) return;
  open.delete(id);
  try { port.postMessage({ kind: "cancel", id }); port.disconnect(); } catch (e) {}
});

function attach() {
  chrome.webAuthenticationProxy.attach().then((err) => { if (err) console.warn("Dex Passkeys:", err); }).catch(() => {});
}
chrome.runtime.onInstalled.addListener(attach);
chrome.runtime.onStartup.addListener(attach);
attach();
