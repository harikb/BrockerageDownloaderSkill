#!/usr/bin/env python3
"""
E*Trade Trade Confirmation Downloader
---------------------------------------
Downloads all trade confirmation PDFs from E*Trade (2019–2025) into an
organized folder structure, using Chrome browser automation.

Prerequisites:
  - Chrome open and logged into E*Trade at:
      https://us.etrade.com/etx/pxy/accountdocs#/documents
  - View > Developer > Allow JavaScript from Apple Events (enabled in Chrome)
  - Chrome setting: "Ask where to save each file" turned OFF
      (chrome://settings/downloads)

Usage:
  python3 etrade_download.py --output-dir /path/to/output/folder

Output structure:
  output-folder/
    2019/TradeConfirmationMMDDYYYY.pdf
    2020/TradeConfirmationMMDDYYYY.pdf
    ...
    2025/TradeConfirmationMMDDYYYY.pdf
"""

import subprocess, time, os, re, glob, argparse

# ── Configuration ─────────────────────────────────────────────────────────────
ETRADE_URL_FRAGMENT = "etrade.com/etx/pxy/accountdocs"
YEARS = ["2025", "2024", "2023", "2022", "2021", "2020", "2019"]
DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
DOWNLOAD_TIMEOUT_SEC = 25
# ──────────────────────────────────────────────────────────────────────────────


def run_js(js_code):
    """Execute JavaScript in the E*Trade Chrome tab and return the result."""
    import json, tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(js_code)
        jsfile = f.name
    js_str = json.dumps(open(jsfile).read())
    os.unlink(jsfile)
    script = f'''
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if URL of t contains "{ETRADE_URL_FRAGMENT}" then
        set r to execute t javascript {js_str}
        return r
      end if
    end repeat
  end repeat
end tell'''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip()


def select_year(year):
    """Open the Timeframe dropdown and select the given year, then apply."""
    print(f"  Selecting year {year}...", end=" ", flush=True)

    # Open the Timeframe mat-select (index 2: Account, DocType, Timeframe)
    run_js("""
var s = document.querySelectorAll('mat-select')[2];
s.focus();
s.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
""")
    time.sleep(1.2)

    # Click the matching year option in the CDK overlay
    run_js(f"""
var panel = document.querySelector('.cdk-overlay-container');
var items = Array.from(panel.querySelectorAll('mat-option, [role=option], li'));
var opt = items.find(function(i) {{ return i.textContent.trim() === '{year}'; }});
if (opt) opt.click();
""")
    time.sleep(0.8)

    # Click Apply
    run_js("""
var btns = Array.from(document.querySelectorAll('button'));
var apply = btns.find(function(b) { return b.textContent.trim() === 'Apply'; });
if (apply) apply.click();
""")
    time.sleep(3)
    print("done")


def get_docs():
    """Return list of (date_str, aria_label) for all documents on the current page."""
    raw = run_js("""
var links = Array.from(document.querySelectorAll('a[aria-label*="PDF"]'));
var slots = document.querySelectorAll('div[slot*="stackedDate"]');
var dates = Array.from(slots).map(function(s) {
  return (s.innerText || '').trim().replace(/\\s+/g, ' ');
});
links.map(function(l, i) {
  return (dates[i] || 'unknown') + '|||' + l.getAttribute('aria-label');
}).join('~~~');
""")
    if not raw or raw == 'missing value':
        return []
    docs = []
    for entry in raw.split('~~~'):
        entry = entry.strip()
        if '|||' in entry:
            parts = entry.split('|||')
            docs.append((parts[0].strip(), parts[-1].strip()))
    return docs


def wait_for_new_pdf(before_files, timeout=DOWNLOAD_TIMEOUT_SEC):
    """Poll ~/Downloads until a new completed PDF appears."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.7)
        current = set(glob.glob(os.path.join(DOWNLOADS_DIR, "*.pdf")))
        new = current - before_files
        if new:
            time.sleep(1.0)  # let the file finish writing
            return list(new)[0]
    return None


def make_filename(date_str, existing_names):
    """
    Convert a date string like '12/29/25' to 'TradeConfirmation12292025.pdf'.
    Appends _B, _C etc. if the filename already exists (same-day duplicates).
    """
    first = date_str.split()[0] if date_str else ''
    m = re.match(r'(\d+)/(\d+)/(\d+)', first)
    if m:
        mm, dd, yy = m.groups()
        base = f"TradeConfirmation{mm.zfill(2)}{dd.zfill(2)}20{yy}.pdf"
    else:
        base = "TradeConfirmation_unknown.pdf"

    if base not in existing_names:
        existing_names.add(base)
        return base

    for suffix in list('BCDEFG'):
        alt = base.replace('.pdf', f'_{suffix}.pdf')
        if alt not in existing_names:
            existing_names.add(alt)
            return alt

    return base  # fallback (unlikely)


def ensure_year_dirs(output_dir):
    for year in YEARS:
        os.makedirs(os.path.join(output_dir, year), exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Download E*Trade trade confirmations by year.")
    parser.add_argument("--output-dir", required=True,
                        help="Root folder; year subfolders will be created inside it")
    args = parser.parse_args()

    output_dir = args.output_dir
    ensure_year_dirs(output_dir)

    # Verify tab is open
    test = run_js("document.title")
    if not test or "E*TRADE" not in test:
        print("ERROR: E*Trade Documents tab not found in Chrome.")
        print("Please open: https://us.etrade.com/etx/pxy/accountdocs#/documents")
        return

    # Make sure Trade Confirmations filter is selected
    run_js("""
var els = Array.from(document.querySelectorAll('*'));
var tc = els.find(function(e) {
  return (e.textContent || '').trim() === 'Trade confirmations' && e.children.length <= 2;
});
if (tc && tc.parentElement) tc.parentElement.click();
""")
    time.sleep(2)

    grand_total = 0

    for year in YEARS:
        print(f"\n{'='*40}")
        print(f"Year: {year}")
        print('='*40)

        select_year(year)
        docs = get_docs()
        print(f"  Found {len(docs)} documents")

        year_dir = os.path.join(output_dir, year)
        existing_names = set()

        for idx, (date_str, label) in enumerate(docs):
            fname = make_filename(date_str, existing_names)
            outfile = os.path.join(year_dir, fname)
            print(f"  [{idx+1}/{len(docs)}] {date_str} -> {fname}", end=" ", flush=True)

            # Snapshot Downloads folder before triggering download
            before = set(glob.glob(os.path.join(DOWNLOADS_DIR, "*.pdf")))

            # Trigger download via JS click (no dialog — Chrome saves silently)
            run_js(f'document.querySelectorAll(\'a[aria-label*="PDF"]\')[{idx}].click();')

            # Wait for new file to land in Downloads
            new_file = wait_for_new_pdf(before)
            if not new_file:
                print("FAILED (timeout — no file in Downloads)")
                continue

            # Move to output folder with clean name
            os.rename(new_file, outfile)
            size = os.path.getsize(outfile)
            print(f"OK ({size // 1024}KB)")
            time.sleep(0.5)

        count = len(glob.glob(os.path.join(year_dir, "*.pdf")))
        grand_total += count
        print(f"  Year {year}: {count} files saved")

    print(f"\n{'='*40}")
    print(f"All done — {grand_total} files total")
    print(f"Saved to: {output_dir}")
    print('='*40)


if __name__ == "__main__":
    main()
