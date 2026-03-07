# Agent-Browser Command Reference

Source: https://agent-browser.dev/commands

## Core Navigation & Interaction

**Navigation:**
- `agent-browser open <url>` - Navigate to URL (aliases: goto, navigate)
- `agent-browser back` - Go back
- `agent-browser forward` - Go forward
- `agent-browser reload` - Reload page

**Clicking & Selection:**
- `agent-browser click <sel>` - Click element (--new-tab flag opens in new tab)
- `agent-browser dblclick <sel>` - Double-click
- `agent-browser select <sel> <val>` - Select dropdown option

**Text Input:**
- `agent-browser fill <sel> <text>` - Clear and fill field
- `agent-browser type <sel> <text>` - Type into element
- `agent-browser keyboard type <text>` - Type at current focus without selector
- `agent-browser keyboard inserttext <text>` - Insert text bypassing key events

**Key Operations:**
- `agent-browser press <key>` - Press key like Enter, Tab, Control+a
- `agent-browser keydown <key>` - Hold key down
- `agent-browser keyup <key>` - Release key

## Element Interaction

**Hover & Focus:**
- `agent-browser hover <sel>` - Hover element
- `agent-browser focus <sel>` - Focus element

**Checkboxes:**
- `agent-browser check <sel>` - Check checkbox
- `agent-browser uncheck <sel>` - Uncheck checkbox

**Scrolling:**
- `agent-browser scroll <dir> [px]` - Scroll up/down/left/right
- `agent-browser scrollintoview <sel>` - Scroll element into view

**Drag & Upload:**
- `agent-browser drag <src> <dst>` - Drag and drop
- `agent-browser upload <sel> <files>` - Upload files

## File Downloads

- `agent-browser download <sel> <path>` - Click element to trigger download
- `agent-browser wait --download [path]` - Wait for download completion
- Use `--download-path <dir>` or `AGENT_BROWSER_DOWNLOAD_PATH` env var for default download dir

## Page Information & State

- `agent-browser get text <sel>` - Get text content
- `agent-browser get html <sel>` - Get innerHTML
- `agent-browser get value <sel>` - Get input value
- `agent-browser get attr <sel> <attr>` - Get attribute
- `agent-browser get title` - Get page title
- `agent-browser get url` - Get current URL
- `agent-browser get count <sel>` - Count matching elements
- `agent-browser get box <sel>` - Get bounding box
- `agent-browser get styles <sel>` - Get computed styles
- `agent-browser is visible <sel>` - Check visibility
- `agent-browser is enabled <sel>` - Check if enabled
- `agent-browser is checked <sel>` - Check if checked

## Semantic Element Finding

- `agent-browser find role <role> <action> [value]`
- `agent-browser find text <text> <action>`
- `agent-browser find label <label> <action> [value]`
- `agent-browser find placeholder <ph> <action> [value]`
- `agent-browser find alt <text> <action>`
- `agent-browser find title <text> <action>`
- `agent-browser find testid <id> <action>`
- `agent-browser find first <sel> <action> [value]`
- `agent-browser find last <sel> <action> [value]`
- `agent-browser find nth <n> <sel> <action> [value]`
- Options: `--name <name>` (filter role by name), `--exact` (exact text match)

## Dialog Handling

- `agent-browser dialog accept [text]` - Accept dialog
- `agent-browser dialog dismiss` - Dismiss dialog

## Waiting & Conditions

- `agent-browser wait <selector>` - Wait for element
- `agent-browser wait <ms>` - Wait for duration
- `agent-browser wait --text "text"` - Wait for text
- `agent-browser wait --url "**/path"` - Wait for URL pattern
- `agent-browser wait --load networkidle` - Wait for load state
- `agent-browser wait --fn "condition"` - Wait for JS condition
- `agent-browser wait --download [path]` - Wait for download

## Screenshots & Capture

- `agent-browser screenshot [path]` - Screenshot (--full for full page, --annotate for labels)
- `agent-browser pdf <path>` - Save as PDF
- `agent-browser snapshot` - Accessibility tree with element refs

## Browser Control

- `agent-browser eval <js>` - Run JavaScript
- `agent-browser connect <port|url>` - Connect via CDP
- `agent-browser close` - Close browser
