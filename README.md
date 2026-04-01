# Brokerage Trade Confirmation Downloader

Automates downloading trade confirmation PDFs from **Fidelity** and **E*Trade** using
Chrome browser automation (AppleScript + JavaScript). No manual clicking required.

## How It Works

The scripts control your already-logged-in Chrome browser via AppleScript. They:
1. Set year filters on the brokerage website using JavaScript
2. Click each PDF link programmatically
3. Let Chrome download to `~/Downloads` (using your real browser session/cookies)
4. Move each file to the correct `[year]/` subfolder with a clean filename

This approach works because Chrome uses its full cookie jar (including HttpOnly session
cookies) when downloading — no need to extract or replay cookies manually.

---

## Prerequisites

### 1. Chrome Setting
Disable "Ask where to save each file before downloading":
- Open `chrome://settings/downloads` in Chrome
- Turn off **"Ask where to save each file before downloading"**
- Chrome will now silently save all downloads to `~/Downloads`

### 2. Enable JavaScript from Apple Events (one-time)
In Chrome menu: **View → Developer → Allow JavaScript from Apple Events**

### 3. Be Logged In
Make sure you are already logged into Fidelity / E*Trade in Chrome before running.

### 4. Python 3
Both scripts require Python 3 (standard macOS install is fine).

---

## Fidelity: Verify Local Downloads

`fidelity_check.py` — Reads the Fidelity trade confirmations page, expands all years
using "Show More", and compares counts against your local folder.

### Usage
```bash
python3 fidelity_check.py --local-dir /path/to/your/Fidelity/folder
```

### What it does
- Connects to the open Fidelity tab in Chrome (`digitalservices.fidelity.com`)
- For each year (2017–2025), sets the year filter and clicks "Show More" until all
  results are visible
- Counts documents on the website per year
- Counts PDFs in your local folder per year
- Prints a comparison table

---

## E*Trade: Download All Trade Confirmations

`etrade_download.py` — Downloads all trade confirmations from E*Trade for years
2019–2025 into an organized folder structure.

### Usage
```bash
python3 etrade_download.py --output-dir /path/to/output/folder
```

This creates:
```
output-folder/
  2019/TradeConfirmationMMDDYYYY.pdf
  2020/TradeConfirmationMMDDYYYY.pdf
  ...
  2025/TradeConfirmationMMDDYYYY.pdf
```

Duplicate dates (multiple trades same day) get `_B`, `_C` suffixes automatically.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Tab not found" | Make sure you're logged in and the brokerage page is open in Chrome |
| Timeout / no file appears | The session may have expired — refresh the page and re-run |
| Wrong year selected | The E*Trade dropdown selector uses `mat-select[2]` — if the page layout changes, inspect the selectors |
| Files not moving | Check that `~/Downloads` is the Chrome download destination |
# BrockerageDownloader
