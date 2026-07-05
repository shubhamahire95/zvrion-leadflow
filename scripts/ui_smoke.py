"""Small local browser smoke test for responsive LeadFlow releases."""
from playwright.sync_api import sync_playwright

SIZES = [(320, 700), (768, 900), (1366, 900), (1920, 1080)]
ROUTES = ("dashboard", "new-scrape", "live-leads", "history", "downloads", "settings")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for width, height in SIZES:
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        for route in ROUTES:
            page.goto(f"http://127.0.0.1:8765/#{route}", wait_until="networkidle")
            active = page.locator(".page-section.active")
            assert active.count() == 1 and active.get_attribute("id") == route
            overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            offenders = page.evaluate("""[...document.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1).slice(0,8).map(e => {const r=e.getBoundingClientRect();return [e.tagName,e.className,Math.round(r.left),Math.round(r.width),Math.round(r.right),getComputedStyle(e).minWidth]})""") if overflow else []
            assert not overflow, f"page overflow at {width}px on {route}: {offenders}"
        assert not errors, f"console errors at {width}px: {errors}"
        print(f"{width}x{height}: all routes responsive, no console errors")
        page.close()
    browser.close()
