#!/usr/bin/env python3
"""
Fidelity Trade Confirmation Verifier
-------------------------------------
Reads the Fidelity trade confirmations page in Chrome, expands all results
per year, and compares counts against a local folder of downloaded PDFs.

Prerequisites:
  - Chrome open and logged into Fidelity
  - View > Developer > Allow JavaScript from Apple Events (enabled in Chrome)

Usage:
  python3 fidelity_check.py --local-dir /path/to/your/Fidelity/folder
"""

import subprocess, time, os, glob, argparse

# ── Configuration ─────────────────────────────────────────────────────────────
FIDELITY_URL_FRAGMENT = "digitalservices.fidelity.com"
YEARS = ["2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]
# ──────────────────────────────────────────────────────────────────────────────


def run_js(js_code):
    """Execute JavaScript in the Fidelity Chrome tab and return the result."""
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
      if URL of t contains "{FIDELITY_URL_FRAGMENT}" then
        set r to execute t javascript {js_str}
        return r
      end if
    end repeat
  end repeat
end tell'''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip()


def set_year_filter(year):
    """Select a year in the Fidelity date filter dropdown."""
    run_js(f"""
var sel = document.getElementById('options-select-TimeFilter');
sel.value = '{year}';
sel.dispatchEvent(new Event('change', {{bubbles: true}}));
""")
    time.sleep(2.5)


def expand_all(max_clicks=20):
    """Click 'Show More' until all results are visible."""
    for _ in range(max_clicks):
        result = run_js("""
var links = Array.from(document.querySelectorAll('a.pvd-link__link'));
var btn = links.find(function(a) { return (a.textContent || '').trim() === 'Show More'; });
if (btn) { btn.click(); 'clicked'; } else { 'done'; }
""")
        if result == 'done':
            break
        time.sleep(2.5)


def count_online(year):
    """Return number of trade confirmation rows for the given year."""
    set_year_filter(year)
    expand_all()
    count = run_js("document.querySelectorAll('tr').length - 1")
    try:
        return int(count)
    except (ValueError, TypeError):
        return 0


def count_local(local_dir, year):
    """Count PDF files in local_dir/year/."""
    year_dir = os.path.join(local_dir, year)
    if not os.path.isdir(year_dir):
        return 0
    return len(glob.glob(os.path.join(year_dir, "*.pdf")))


def main():
    parser = argparse.ArgumentParser(description="Compare Fidelity online vs local trade confirmations.")
    parser.add_argument("--local-dir", required=True, help="Path to local folder with year subfolders")
    args = parser.parse_args()

    # Verify tab is open
    test = run_js("document.title")
    if not test or "Fidelity" not in test:
        print("ERROR: Fidelity tab not found in Chrome. Make sure you are logged in.")
        return

    print(f"\n{'Year':<6} {'Online':>8} {'Local':>8} {'Match':>7}")
    print("-" * 32)

    total_online, total_local = 0, 0
    for year in YEARS:
        online = count_online(year)
        local  = count_local(args.local_dir, year)
        match  = "OK" if online == local else "MISMATCH"
        print(f"{year:<6} {online:>8} {local:>8} {match:>7}")
        total_online += online
        total_local  += local

    print("-" * 32)
    total_match = "OK" if total_online == total_local else "MISMATCH"
    print(f"{'TOTAL':<6} {total_online:>8} {total_local:>8} {total_match:>7}")


if __name__ == "__main__":
    main()
