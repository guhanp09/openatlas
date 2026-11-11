"""Browser verification against the evaluated local index; run after evaluate."""

import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import joblib
from playwright.sync_api import sync_playwright

from openatlas.server import handler_for


def main():
    root = Path.cwd()
    model = joblib.load(root / "models/search.joblib")
    examples = json.loads((root / "models/examples.json").read_text())
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(model["index"], model["weight"], examples))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=os.environ.get("OPENATLAS_BROWSER_CHANNEL"))
            browser_version = browser.version
            page = browser.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=1)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}")
            for lang, code in [("english", "en"), ("bengali", "bn"), ("telugu", "te")]:
                page.locator(f'input[name="language"][value="{lang}"]').check()
                page.locator("#question").fill(examples[lang])
                page.locator("#question").press("Enter")
                page.wait_for_function("() => document.querySelector('#status').textContent.includes('sources ·')")
                assert page.locator(f".preview[lang='{code}']").count() > 0
                checks.append(f"{lang}: Unicode question, keyboard submit and language-tagged results")
            compact_ids = page.locator(".result h2 a").evaluate_all("els => els.map(e => e.href)")
            compact_text = page.locator(".preview").all_text_contents()
            page.locator("#saver").uncheck()
            page.wait_for_function(
                "() => document.querySelector('#status').textContent.includes('Expanded previews')"
            )
            assert compact_ids == page.locator(".result h2 a").evaluate_all("els => els.map(e => e.href)")
            assert sum(map(len, page.locator(".preview").all_text_contents())) > sum(map(len, compact_text))
            checks.append("data saver changes preview length while preserving ranked source links")
            page.locator('input[value="english"]').check()
            page.locator("#saver").check()
            page.locator("#question").fill(examples["english"])
            page.locator("#question").press("Enter")
            page.wait_for_function("() => document.querySelector('#status').textContent.includes('sources ·')")
            page.screenshot(path=str(root / "reports/desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(root / "reports/mobile.png"), full_page=True)
            checks.append("390px mobile view has no horizontal overflow")
            page.locator("#question").fill("\ue000" * 20)  # Unindexed private-use characters.
            page.locator("#question").press("Enter")
            page.wait_for_function(
                "() => document.querySelector('#status').textContent.includes('No matching source')"
            )
            assert page.locator(".result").count() == 0
            checks.append("unknown-vocabulary query produces a clear empty state")
            page.locator("#question").fill('<img src=x onerror="window.attack=true">')
            page.locator("#question").press("Enter")
            page.wait_for_function("() => document.querySelector('#results').getAttribute('aria-busy') === 'false'")
            assert page.evaluate("() => window.attack === undefined")
            assert page.locator("#results img").count() == 0
            checks.append("query markup does not execute or insert HTML")
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    report = {
        "browser_version": browser_version,
        "browser_channel": os.environ.get("OPENATLAS_BROWSER_CHANNEL", "bundled-chromium"),
        "passed": len(checks),
        "checks": checks,
        "browser_errors": errors,
        "scope": "Automated browser checks; not native-reader usability or accessibility certification",
    }
    (root / "reports/browser_checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
