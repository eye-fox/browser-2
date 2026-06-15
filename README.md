# Browser GitHub Actions

Browser automation via GitHub Actions — Chromium CDP + Selenium.

## Structure

- `browser-local` — Python CDP automation script (same as `/usr/local/bin/browser-local`)
- `selenium/` — Selenium-based fallback automation
- `.github/workflows/browser.yml` — GitHub Actions workflow

## Usage via bridge tool

Pasang `browser-github` di lokal, lalu:

```bash
browser-github --session s1 open "https://example.com"
browser-github --session s1 state
browser-github --session s1 click 0
```

Session di-cache via `actions/cache` — cookies & login state persist antar command.

## Manual trigger

Buka GitHub → Actions → browser → workflow_dispatch → isi `cmd_b64`.

## Selenium

```bash
cd selenium
pip install -r requirements.txt
python3 selenium_browser.py open "https://example.com"
```
