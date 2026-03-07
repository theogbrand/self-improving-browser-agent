---
name: gmail-invoice-download
description: Download invoice attachments from Gmail. Use when the user needs to find and download invoices, receipts, or PDF attachments from their Gmail inbox. Triggers include "download invoice from email", "find invoice in Gmail", "get receipt from email", "download attachment from Gmail", or any task requiring finding and saving email attachments.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*)
---

# Gmail Invoice Download

Find and download invoice/receipt attachments from Gmail.

## Critical Rules

### Command Chaining in agent-browser

When chaining commands, EVERY command must be prefixed with `agent-browser`. The shell does not know what `press`, `wait`, `fill`, or `snapshot` are on their own.

```bash
# WRONG - will fail with "command not found"
agent-browser fill @e5 "query" && press Enter && wait 2000 && snapshot -i

# CORRECT - every command has the agent-browser prefix
agent-browser fill @e5 "query" && agent-browser press Enter && agent-browser wait 2000 && agent-browser snapshot -i
```

**Preferred approach:** Run commands one at a time (separate tool calls) so you can read each output before deciding the next step. Only chain when you do NOT need intermediate output.

### Gmail-Specific Waits

Gmail uses persistent WebSocket connections. `wait --load networkidle` will ALWAYS time out on Gmail.

```bash
# WRONG - will timeout
agent-browser wait --load networkidle

# CORRECT - use time-based waits on Gmail
agent-browser wait 2000
```

## Step-by-Step Workflow

### Step 1: Navigate to Gmail

```bash
agent-browser open https://mail.google.com
agent-browser wait 3000
agent-browser snapshot -i
```

If not logged in, you'll need to authenticate first. If already logged in via an existing Chrome session, use `--cdp <port>` to connect.

### Step 2: Search for Invoices

Use Gmail's search bar with **precise search operators**. Combine multiple operators in a single query for best results.

**Gmail Search Operators:**
| Operator | Example | Description |
|----------|---------|-------------|
| `from:` | `from:brandon` | Sender name or email |
| `subject:` | `subject:invoice` | Words in subject line |
| `has:attachment` | `has:attachment` | Only emails with attachments |
| `filename:` | `filename:pdf` | Attachment file type |
| `after:` | `after:2026/03/01` | Emails after date (YYYY/MM/DD) |
| `before:` | `before:2026/03/31` | Emails before date |
| `newer_than:` | `newer_than:30d` | Emails from last N days |
| `{term1 term2}` | `{cognition warp}` | Match ANY term (OR) |
| `"exact phrase"` | `"invoice attached"` | Exact phrase match |

**Build a precise query upfront. Do NOT search multiple times with vague queries.**

```bash
# Example: Find invoices from Brandon about Cognition or Warp, this month
agent-browser fill @e5 "from:brandon subject:invoice {cognition warp} newer_than:30d"
agent-browser press Enter
agent-browser wait 3000
agent-browser snapshot -i -C
```

If no results, broaden progressively:
1. Remove `subject:invoice`, keep other filters
2. Remove date filter
3. Try `has:attachment` instead of `subject:invoice`

### Step 3: Open the Email Thread (NOT the Attachment Preview)

**CRITICAL:** Gmail search results show both email rows and attachment chips as cursor-interactive elements. Clicking the wrong one opens a **preview overlay** that downloads files with UUID names instead of original filenames.

The `-C` snapshot shows elements like:
```
- clickable "Sender, Fwd: Subject, has attachment, date, preview..." [ref=eXX]  ← email row
- clickable "Attachment:Invoice-ABC123.pdf" [ref=eYY]                            ← attachment chip (DO NOT CLICK)
```

**NEVER click `clickable "Attachment:..."` elements.** They open the preview overlay.

**Even clicking the email row ref can trigger the preview overlay.** The most reliable method is JavaScript `eval`:

```bash
# Open the first email in search results
agent-browser eval 'document.querySelector("tr.zA td.xY").click()'
agent-browser wait 2000
agent-browser snapshot -i -C

# Or target a specific email by content
agent-browser eval 'Array.from(document.querySelectorAll("tr.zA")).find(r => r.textContent.includes("Cognition")).querySelector("td.xY").click()'
agent-browser wait 2000
agent-browser snapshot -i -C
```

The `td.xY` targets the subject cell, which reliably navigates to the email thread.

**Verify you opened the thread, NOT the preview:**
- **Thread view** (correct): URL has `#inbox/FMfcg...` or `#search/.../FMfcg...`. Snapshot shows `button "Back to Inbox"`, `button "Reply"`, `button "Download attachment filename.pdf"`
- **Preview overlay** (wrong): URL has `?projector=1`. Snapshot shows `button "Previous"`, `button "Zoom in"`, `button "Close"`, `button "Download"`

If the preview opened, close it (`agent-browser click @e_close`) and retry with the `eval td.xY` method.

### Step 4: Download Attachments from Thread View

Inside the email thread, the snapshot shows dedicated download buttons with original filenames:

```
- button "Download all attachments" [ref=eXX]                    ← downloads all as zip
- button "Download attachment Invoice-ABC123.pdf" [ref=eYY]      ← single file (USE THIS)
- link "Preview attachment Invoice-ABC123.pdf ..." [ref=eZZ]     ← opens preview (AVOID)
```

**Use `button "Download attachment ..."` elements — these preserve the original filename.**

```bash
# Download a specific attachment
agent-browser download @eYY /Users/ob1/Downloads/Invoice-ABC123.pdf
agent-browser wait --download /Users/ob1/Downloads/Invoice-ABC123.pdf

# Or download all attachments at once
agent-browser download @eXX /Users/ob1/Downloads/
```

**DO NOT click `link "Preview attachment ..."` elements** — they open the preview overlay which downloads with UUID names.

### Step 6: Go Back and Repeat

After downloading from one email, go back to search results for the next invoice.

```bash
agent-browser back
agent-browser wait 2000
agent-browser snapshot -i
# Click the next email...
```

### Step 7: Verify Downloads

```bash
# List downloaded files
agent-browser eval "document.title"  # (just to keep browser active)
```

Then use the `done` tool to report success with the list of downloaded files and their paths.

## Complete Example: Download Cognition and Warp Invoices from Brandon

```bash
# 1. Open Gmail
agent-browser open https://mail.google.com
agent-browser wait 3000
agent-browser snapshot -i

# 2. Search with precise query
agent-browser fill @e5 "from:brandon {cognition warp} invoice has:attachment newer_than:30d"
agent-browser press Enter
agent-browser wait 3000
agent-browser snapshot -i -C

# 3. Open Cognition email thread using eval (avoids preview overlay)
agent-browser eval 'Array.from(document.querySelectorAll("tr.zA")).find(r => r.textContent.includes("Cognition")).querySelector("td.xY").click()'
agent-browser wait 2000
agent-browser snapshot -i -C
# Verify: should see "button Download attachment Invoice-xxx.pdf", NOT "button Zoom in"

# 4. Download the invoice attachment (use the "Download attachment" BUTTON, not the preview link)
# Look for: button "Download attachment Invoice-329EE3B4-0002.pdf" [ref=eXX]
agent-browser download @eXX /Users/ob1/Downloads/Invoice-Cognition.pdf
agent-browser wait --download /Users/ob1/Downloads/Invoice-Cognition.pdf

# 5. Go back to search results
agent-browser back
agent-browser wait 2000

# 6. Open Warp email thread
agent-browser eval 'Array.from(document.querySelectorAll("tr.zA")).find(r => r.textContent.includes("Warp")).querySelector("td.xY").click()'
agent-browser wait 2000
agent-browser snapshot -i -C

# 7. Download Warp invoice
# Look for: button "Download attachment Invoice-W6LCUKAB-0004.pdf" [ref=eYY]
agent-browser download @eYY /Users/ob1/Downloads/Invoice-Warp.pdf
agent-browser wait --download /Users/ob1/Downloads/Invoice-Warp.pdf

# 8. Done — report file paths
```

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| `wait --load networkidle` times out | Use `wait 2000` or `wait 3000` instead |
| Command chaining fails with "command not found" | Prefix EVERY chained command with `agent-browser`, or run commands individually |
| Search returns no results | Broaden query: remove date filter, try different sender format, drop `subject:` |
| **Email rows only show "Not starred" buttons, no links** | Use `snapshot -i -C` to capture cursor-interactive rows, then use `eval` with `td.xY` to click |
| **Downloads have UUID filenames (no extension)** | You clicked an attachment chip or preview link. Always open the email THREAD first, then use `button "Download attachment filename.pdf"` elements |
| **Preview overlay opened instead of email thread** | URL has `?projector=1`. Close it, then use `eval 'document.querySelector("tr.zA td.xY").click()'` |
| Clicking `clickable "Attachment:..."` from search results | Opens preview overlay with broken downloads. NEVER click these — use `eval` to open the email thread |
| Attachments not visible in snapshot | Scroll down in the email, or use `snapshot -i -C` for cursor-interactive elements |
| Download goes to wrong location | Specify an absolute path in the `download` command |
| `fill` replaces previous search instead of appending | `fill` clears the field first (this is correct behavior for new searches) |
| Gmail shows a promo/popup on load | Look for "OK", "No thanks", or "Close" button refs and dismiss first |

## Gmail UI Structure (Accessibility Tree)

Understanding what refs map to in Gmail:

**Inbox/Search results view:**
- `textbox "Search mail"` - The search input field
- `checkbox "sender, subject, date, preview..."` - Email row (for selection)
- `link "subject - preview text"` - Email row (clickable to open)
- `button "Not starred"` - Star toggle (do NOT click this to open email)
- `button "Advanced search options"` - Search filters dropdown
- `button "Clear search"` - Clears current search

**Email detail view (after opening an email):**
- `link "Back to search results"` or `link "Back to Inbox"` - Navigation back
- Message body content (text elements)
- Attachment elements near the bottom (buttons/links with filenames)
- `button "Download"` or download icon within attachment cards

**Common popups/banners:**
- `link "OK"` / `link "No, thanks"` - Consent/notification banners
- `button "Close"` - Dismiss popups
- `button "Got it"` - Tutorial/onboarding prompts

Dismiss these immediately before proceeding with the task.
