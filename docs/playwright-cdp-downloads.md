# Playwright Downloads over CDP (connectOverCDP) -- Research Summary

Last updated: 2026-03-23

## TL;DR

Downloads **partially work** over CDP on the same machine, but with significant caveats.
`page.on('download')` **does fire** over CDP. `download.saveAs()` **fails on remote
connections** but works on same-host. Playwright officially recommends using
`browserType.connect()` (Playwright protocol) instead of `connectOverCDP()` for
reliable download support.

---

## 1. Does `page.on('download')` fire when connected via CDP?

**Yes.** The download event fires correctly over CDP connections. Playwright internally
subscribes to the CDP `Browser.downloadWillBegin` and `Browser.downloadProgress` events,
and these work regardless of whether the browser was launched or connected via CDP.

From the Playwright source (`crBrowser.ts`), the event handling is identical for both
launch and connectOverCDP modes -- there is no conditional logic distinguishing them.

**However**, there are known cases where the event does NOT fire:
- POST-based download requests may not trigger the event over CDP
  (see [#29679](https://github.com/microsoft/playwright/issues/29679))
- Headless mode combined with CDP can cause download events to not fire
  (see [#17281](https://github.com/microsoft/playwright/issues/17281))

## 2. Does Playwright's download path override work over CDP?

**It depends on the deployment topology.**

### Same-host (localhost) connections -- WORKS

When Playwright and the browser are on the same machine (e.g., connecting to
`http://localhost:9222`), download paths work because both processes share the same
filesystem. Playwright sends a local temp path via `Browser.setDownloadBehavior`, and
Chrome writes files there.

Use the `isLocal: true` option when connecting:
```typescript
const browser = await chromium.connectOverCDP('http://localhost:9222', {
  isLocal: true  // enables filesystem optimizations
});
```

### Remote/cross-platform connections -- BROKEN

When the CDP server is on a different machine, `download.saveAs()` fails with:
```
ENOENT: no such file or directory, copyfile '/tmp/playwright-artifacts-XXXXX/guid'
```

This happens because Playwright sends the **client-side** filesystem path to the
remote browser via CDP, and the remote browser cannot write to a path that only exists
on the client machine. The Playwright team has stated:

> "CDP doesn't allow us to access the download on the remote machine."
> -- [Issue #38805](https://github.com/microsoft/playwright/issues/38805)

## 3. Does `Browser.newContext({ acceptDownloads: true })` work over CDP?

**Partially.** There are important caveats:

### How it works internally

When `acceptDownloads` is set, Playwright calls the CDP command:
```
Browser.setDownloadBehavior({
  behavior: 'allowAndName',  // or 'deny'
  browserContextId: contextId,
  downloadPath: downloadsPath,
  eventsEnabled: true
})
```

### Known failures

- **CEF/Electron browsers**: The `Browser.setDownloadBehavior` CDP command fails with
  `"Browser context management is not supported"`
  ([#15370](https://github.com/microsoft/playwright/issues/15370))
- **Selenium coexistence**: Playwright's `connectOverCDP` call **overrides** any
  existing download behavior settings, disabling downloads that were previously working.
  Workaround: re-apply download configuration after the CDP connection
  ([#17281](https://github.com/microsoft/playwright/issues/17281))
- **Custom download paths cannot be set** when connecting over CDP. Playwright always
  uses a temp directory, and there is no API to override it
  ([#10700](https://github.com/microsoft/playwright/issues/10700)). The maintainers
  stated: *"only the launcher of the browser has control over the download folder for
  security reason."*

### The default context quirk

When connecting via CDP, you get the browser's **default context** via
`browser.contexts()[0]`. You cannot create a new context with `acceptDownloads: true`
in the same way as with a launched browser. The default context's download behavior is
set during the CDP handshake.

## 4. Known workarounds for downloads over CDP

### Workaround 1: Use `isLocal: true` for same-host connections (RECOMMENDED)

If you are connecting to a browser on the same machine:
```typescript
const browser = await chromium.connectOverCDP('http://localhost:9222', {
  isLocal: true
});
```
This tells Playwright the filesystem is shared, enabling `download.saveAs()` to work.

### Workaround 2: Use `browserType.connect()` instead of `connectOverCDP()`

Playwright's native protocol (`connect()`) fully supports downloads including cross-machine
scenarios. The Playwright team recommends this approach:

> "Some functionality doesn't function using CDP. You should instead use Playwright's
> communication protocol using `connect()`."
> -- [Issue #34542](https://github.com/microsoft/playwright/issues/34542)

### Workaround 3: Use raw CDP `Browser.setDownloadBehavior` directly

You can bypass Playwright's download abstraction and use CDP commands directly:
```typescript
const session = await page.context().newCDPSession(page);
await session.send('Browser.setDownloadBehavior', {
  behavior: 'allowAndName',
  downloadPath: '/absolute/path/to/downloads',
  eventsEnabled: true
});

// Listen for download events
session.on('Browser.downloadWillBegin', (event) => {
  console.log('Download started:', event.suggestedFilename, event.guid);
});

session.on('Browser.downloadProgress', (event) => {
  if (event.state === 'completed') {
    console.log('Download completed:', event.guid);
    // File is at: downloadPath/event.guid
  }
});
```

### Workaround 4: Re-apply download config after CDP connection

If downloads stop working after `connectOverCDP()` (because Playwright overrides the
download behavior), re-send the CDP command:
```typescript
const session = await browser.contexts()[0].newCDPSession(
  browser.contexts()[0].pages()[0]
);
await session.send('Browser.setDownloadBehavior', {
  behavior: 'allow',
  downloadPath: '/desired/download/path'
});
```

### Workaround 5: Let the browser download natively

Instead of using Playwright's download abstraction, let Chrome handle downloads to its
default location (configured via Chrome launch flags or user preferences), then read the
files from that known location after a wait. This is what this project's system prompt
already recommends:

```
agent-browser download @eYY /Users/ob1/Downloads/file.pdf
agent-browser wait 3000  # wait for download to complete
```

### Workaround 6: Network interception (advanced)

For remote connections, intercept the download at the network level using CDP:
- `Fetch.requestPaused` to intercept the download request
- `IO.read` to stream the response body
- Write the content locally

This is complex but provides full control.

## 5. How agent-browser handles downloads over CDP

The `agent-browser` CLI (v0.21.4, compiled Rust binary wrapping a Node.js Playwright daemon)
provides:

- `agent-browser download <selector> <path>` -- clicks an element to trigger a download
  and saves to the given path
- `agent-browser wait --download [path]` -- waits for a download to complete
- `--download-path <dir>` or `AGENT_BROWSER_DOWNLOAD_PATH` env var -- sets the default
  download directory for the session

Since agent-browser is a compiled binary, the exact implementation is not inspectable.
However, based on its Playwright foundation and behavior:

1. It likely uses `page.waitForEvent('download')` + `download.saveAs()` internally
2. When connected via `--cdp <port>` to a localhost browser, downloads work because the
   filesystem is shared
3. The `AGENT_BROWSER_DOWNLOAD_PATH` env var is passed through by this project's
   `agent.ts` orchestrator

### This project's current approach

The project connects to a local Brave/Chrome browser via CDP on port 9222 (same machine),
so **downloads work** via the shared filesystem. The system prompt instructs the agent to:
1. Use `agent-browser download @ref /Users/ob1/Downloads/file.pdf` to trigger downloads
2. Use `agent-browser wait 3000` (simple delay) rather than `wait --download` which is
   noted as "fragile" in Gmail contexts
3. Always use absolute paths for downloads

## 6. CDP Protocol: Download-related commands and events

### Commands
- `Browser.setDownloadBehavior` (experimental) -- set behavior to `deny`, `allow`,
  `allowAndName`, or `default`; specify `downloadPath` and `eventsEnabled`

### Events
- `Browser.downloadWillBegin` (experimental) -- fired when download starts; provides
  `frameId`, `guid`, `url`, `suggestedFilename`
- `Browser.downloadProgress` (experimental) -- fired as download progresses; provides
  `guid`, `totalBytes`, `receivedBytes`, `state` (inProgress/completed/canceled)

### Deprecated (use Browser domain instead)
- `Page.downloadWillBegin` -- deprecated, use `Browser.downloadWillBegin`
- `Page.downloadProgress` -- deprecated, use `Browser.downloadProgress`
- `Page.setDownloadBehavior` -- deprecated, use `Browser.setDownloadBehavior`

## 7. Summary table

| Feature | Launch | connectOverCDP (local) | connectOverCDP (remote) |
|---|---|---|---|
| `page.on('download')` fires | Yes | Yes | Yes |
| `download.saveAs()` works | Yes | Yes (with `isLocal: true`) | No (ENOENT) |
| `acceptDownloads: true` | Yes | Yes | Partial (event fires, save fails) |
| Custom download path | Yes | Via CDP command | No |
| `download.suggestedFilename()` | Yes | Yes | Yes |
| `download.path()` | Yes | Returns remote path | Returns remote path (inaccessible) |
| POST-triggered downloads | Yes | May fail | May fail |

## Sources

- [#17281 - Downloads not working with connectOverCDP in headless mode](https://github.com/microsoft/playwright/issues/17281)
- [#15370 - Protocol error Browser.setDownloadBehavior: context management not supported](https://github.com/microsoft/playwright/issues/15370)
- [#29679 - connect_over_cdp with POST download requests](https://github.com/microsoft/playwright/issues/29679)
- [#34542 - download.saveAs fails with CDP connection](https://github.com/microsoft/playwright/issues/34542)
- [#38805 - Cross-platform CDP download path issue](https://github.com/microsoft/playwright/issues/38805)
- [#10700 - Custom downloadsPath with CDP connection](https://github.com/microsoft/playwright/issues/10700)
- [#30383 - Why is setDownloadBehavior required for connect_over_cdp](https://github.com/microsoft/playwright/issues/30383)
- [Playwright Downloads docs](https://playwright.dev/docs/downloads)
- [Playwright BrowserType.connectOverCDP docs](https://playwright.dev/docs/api/class-browsertype)
- [Chrome DevTools Protocol - Browser domain](https://chromedevtools.github.io/devtools-protocol/tot/Browser/)
- [Browser-Use: Leaving Playwright for CDP](https://browser-use.com/posts/playwright-to-cdp)
- [Rebrowser: How to access downloads](https://rebrowser.net/docs/how-to-access-downloads)
