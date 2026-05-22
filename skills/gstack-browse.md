---
name: gstack-browse
description: |
  Headless browser adapted from gstack. Navigate URLs, interact with elements,
  take annotated screenshots, verify page state. ~100ms per command after first use.
  Adapted from garrytan/gstack browse daemon.
trigger: browse, open browser, test the website, take screenshot, navigate to, headless browser, qa the site
tools:
  - browse_navigate
  - browse_snapshot
  - browse_click
  - browse_fill
  - browse_type
  - browse_screenshot
  - browse_scroll
  - browse_js
  - browse_get_text
  - browse_get_html
  - browse_back
  - browse_reload
  - browse_status
category: browser
source: https://github.com/garrytan/gstack
---

# Headless Browser (gstack Browse)

Adapted from garrytan/gstack browse daemon. Real Chromium, real clicks, real screenshots.

## How it works

The gstack browse daemon runs a persistent Chromium controlled via HTTP:
- First command starts the server (~3s)
- Every command after: ~100-200ms
- Tabs, cookies, sessions persist across commands

## Browser Workflow

### 1. Navigate to a page

```
browse_navigate to the target URL
```

### 2. See what's there

```
browse_snapshot  → returns compact text view with @e1, @e2 refs
```

The snapshot shows interactive elements as `@e1 [button] "Submit"`, `@e2 [textbox]`, etc.
Use these refs for all interactions.

### 3. Interact

```
browse_click @e3        → click a button/link
browse_fill @e2 "value" → type into a text field
browse_type "text"      → type into focused element
browse_scroll           → scroll the page
```

### 4. Inspect

```
browse_get_text         → all visible text
browse_get_html         → page HTML source
browse_js "expression"  → run JavaScript in the page
browse_screenshot       → take a screenshot
```

### 5. Navigate

```
browse_back             → go back
browse_reload           → refresh
browse_navigate url2    → go somewhere else
```

## QA Flow (Testing a Website)

1. Navigate to the site
2. Snapshot to see the page structure
3. Click through user flows (login, search, checkout)
4. Take screenshots at key states
5. Verify expected elements are present
6. Test edge cases: empty forms, invalid inputs, long text

## Tips

- Always `browse_snapshot` after navigation to see the page
- Use `browse_js` to check runtime state: `"document.querySelector('.error')"`
- Screenshots help with visual verification
- The browser stays open between commands — sessions persist
