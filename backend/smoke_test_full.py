"""
Comprehensive browser smoke test for PortWatch.
Tests all major UI flows with real API data and captures screenshots.
"""
import asyncio
import sys
import json
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\KIIT0001\Desktop\portwatch\smoke_screenshots"
BRAIN_DIR = r"C:\Users\KIIT0001\.gemini\antigravity\brain\c847e326-efee-4258-b574-e133f8180834"

import os
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

console_errors = []
page_errors = []
network_errors = []
warnings = []
all_console = []

async def main():
    print("=" * 60)
    print("PORTWATCH COMPREHENSIVE BROWSER SMOKE TEST")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # ── Event listeners ────────────────────────────────────
        def on_console(msg):
            entry = "[%s] %s" % (msg.type.upper(), msg.text)
            all_console.append(entry)
            if msg.type == "error":
                console_errors.append(msg.text)
            elif msg.type == "warning":
                warnings.append(msg.text)

        def on_pageerror(err):
            page_errors.append(str(err))
            print("  [PAGE ERROR] %s" % str(err), file=sys.stderr)

        def on_response(response):
            if response.status >= 400:
                network_errors.append("%s %s -> %s" % (response.request.method, response.url, response.status))

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)
        page.on("response", on_response)

        # ══════════════════════════════════════════════════════
        # TEST 1: Initial page load
        # ══════════════════════════════════════════════════════
        print("\n[TEST 1] Loading main page...")
        try:
            await page.goto("http://localhost:5173", timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(3)  # Let React hydrate and API calls settle
            print("  Page loaded successfully")
        except Exception as e:
            print("  FAILED: %s" % e, file=sys.stderr)

        title = await page.title()
        print("  Title: %s" % title)

        # Check that the navbar renders
        navbar = await page.query_selector('nav, [class*="navbar"], [class*="Navbar"]')
        print("  Navbar rendered: %s" % (navbar is not None))

        # Check vessel count badge
        vessel_count_el = await page.query_selector('[class*="vessel-count"], [class*="badge"]')
        if vessel_count_el:
            text = await vessel_count_el.inner_text()
            print("  Vessel count badge: %s" % text)
        else:
            print("  Vessel count badge: not found (checking other selectors)")
            # Try to find it by text content
            badge = await page.locator("text=/\\d+\\s*VESSELS/i").first.text_content()
            print("  Found vessel text: %s" % badge if badge else "  No vessel count found")

        # Check that the Leaflet map container exists
        map_el = await page.query_selector('.leaflet-container')
        print("  Leaflet map rendered: %s" % (map_el is not None))

        # Check for map tiles loaded
        tiles = await page.query_selector_all('.leaflet-tile-loaded')
        print("  Map tiles loaded: %s" % len(tiles))

        # Check for vessel markers on the map
        markers = await page.query_selector_all('.leaflet-marker-icon, [class*="vessel-marker"], svg circle, .leaflet-marker-pane *')
        print("  Vessel markers on map: %s" % len(markers))

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_initial_load.png"))
        print("  Screenshot: 01_initial_load.png")

        # ══════════════════════════════════════════════════════
        # TEST 2: Click a vessel marker on the map
        # ══════════════════════════════════════════════════════
        print("\n[TEST 2] Clicking a vessel marker...")
        marker = await page.query_selector('.leaflet-marker-icon, [class*="vessel-marker"], .leaflet-marker-pane > *')
        if marker:
            try:
                await marker.click(timeout=3000)
                await asyncio.sleep(2)
                print("  Clicked vessel marker")
            except Exception as e:
                print("  Could not click marker: %s" % e)
        else:
            # Try zooming into a cluster first
            print("  No individual markers found, trying to zoom into cluster...")
            cluster = await page.query_selector('.leaflet-marker-icon')
            if cluster:
                await cluster.dblclick()
                await asyncio.sleep(1)
                # Try again
                marker = await page.query_selector('.leaflet-marker-icon')
                if marker:
                    await marker.click(timeout=3000)
                    await asyncio.sleep(2)
                    print("  Clicked vessel marker after zoom")

        # Check if vessel detail panel opened
        panel = await page.query_selector('[class*="panel"], [class*="Panel"], [class*="detail"], [class*="Detail"]')
        if panel:
            panel_visible = await panel.is_visible()
            print("  Vessel detail panel visible: %s" % panel_visible)
            if panel_visible:
                panel_text = await panel.inner_text()
                # Print first 200 chars
                print("  Panel content preview: %s..." % panel_text[:200].replace("\n", " "))
        else:
            print("  Vessel detail panel: not found after click")

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_vessel_click.png"))
        print("  Screenshot: 02_vessel_click.png")

        # ══════════════════════════════════════════════════════
        # TEST 3: Test the search functionality (Ctrl+K)
        # ══════════════════════════════════════════════════════
        print("\n[TEST 3] Testing search (Ctrl+K)...")
        # Close any open panel first by pressing Escape
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        await page.keyboard.press("Control+k")
        await asyncio.sleep(1)

        search_input = await page.query_selector('input[type="text"], input[type="search"], [class*="search"] input')
        if search_input:
            print("  Search modal opened: True")
            await search_input.fill("Shadow")
            await asyncio.sleep(2)  # Wait for search results

            # Check for search results
            results = await page.query_selector_all('[class*="result"], [class*="Result"], [class*="search"] li, [class*="search"] [class*="item"]')
            print("  Search results found: %s" % len(results))

            if results:
                first_result_text = await results[0].inner_text()
                print("  First result: %s" % first_result_text[:100].replace("\n", " "))
                # Click the first result
                try:
                    await results[0].click(timeout=3000)
                    await asyncio.sleep(2)
                    print("  Clicked first search result")
                except Exception as e:
                    print("  Could not click result: %s" % e)
        else:
            print("  Search modal opened: False (input not found)")

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_search.png"))
        print("  Screenshot: 03_search.png")

        # ══════════════════════════════════════════════════════
        # TEST 4: Test sidebar / filter panel
        # ══════════════════════════════════════════════════════
        print("\n[TEST 4] Testing sidebar filters...")
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        # Click the hamburger/sidebar toggle
        sidebar_btn = await page.query_selector('[class*="hamburger"], [class*="sidebar-toggle"], [class*="menu-btn"], button:first-child')
        if sidebar_btn:
            try:
                await sidebar_btn.click(timeout=3000)
                await asyncio.sleep(1)
                print("  Sidebar toggle clicked")
            except Exception as e:
                print("  Could not click sidebar toggle: %s" % e)

        sidebar = await page.query_selector('[class*="sidebar"], [class*="Sidebar"]')
        if sidebar:
            sidebar_visible = await sidebar.is_visible()
            print("  Sidebar visible: %s" % sidebar_visible)
            sidebar_text = await sidebar.inner_text()
            print("  Sidebar content preview: %s..." % sidebar_text[:200].replace("\n", " "))
        else:
            print("  Sidebar: not found")

        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_sidebar.png"))
        print("  Screenshot: 04_sidebar.png")

        # ══════════════════════════════════════════════════════
        # TEST 5: Verify API data loads into the enriched view
        # ══════════════════════════════════════════════════════
        print("\n[TEST 5] Verifying enriched vessel data via API...")
        # Navigate to the enriched endpoint directly via the API
        api_response = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels?per_page=5');
                    const data = await r.json();
                    return JSON.stringify({
                        status: r.status,
                        total: data.total,
                        first_vessel: data.items && data.items[0] ? data.items[0].name : null,
                        items_count: data.items ? data.items.length : 0
                    });
                } catch(e) {
                    return JSON.stringify({error: e.message});
                }
            }
        """)
        api_data = json.loads(api_response)
        print("  API /vessels status: %s" % api_data.get("status"))
        print("  Total vessels: %s" % api_data.get("total"))
        print("  Items returned: %s" % api_data.get("items_count"))
        print("  First vessel: %s" % api_data.get("first_vessel"))

        # Test enriched endpoint
        enriched_response = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/enriched/vessels');
                    const data = await r.json();
                    return JSON.stringify({
                        status: r.status,
                        count: Array.isArray(data) ? data.length : (data.items ? data.items.length : 'unknown'),
                        sample: Array.isArray(data) && data[0] ? {
                            name: data[0].name,
                            imo: data[0].imo,
                            risk_score: data[0].risk_score,
                            lat: data[0].latitude,
                            lon: data[0].longitude,
                            type: data[0].type || data[0].vessel_type
                        } : null
                    });
                } catch(e) {
                    return JSON.stringify({error: e.message});
                }
            }
        """)
        enriched_data = json.loads(enriched_response)
        print("  API /enriched/vessels status: %s" % enriched_data.get("status"))
        print("  Enriched vessels count: %s" % enriched_data.get("count"))
        if enriched_data.get("sample"):
            s = enriched_data["sample"]
            print("  Sample vessel: name=%s, imo=%s, risk=%s, lat=%s, lon=%s, type=%s" % (
                s.get("name"), s.get("imo"), s.get("risk_score"), s.get("lat"), s.get("lon"), s.get("type")
            ))
        if enriched_data.get("error"):
            print("  ERROR: %s" % enriched_data["error"])

        # Test ownership
        ownership_response = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels/9100000/ownership');
                    const data = await r.json();
                    return JSON.stringify({
                        status: r.status,
                        nodes: data.nodes ? data.nodes.length : 0,
                        edges: data.edges ? data.edges.length : 0
                    });
                } catch(e) {
                    return JSON.stringify({error: e.message});
                }
            }
        """)
        own_data = json.loads(ownership_response)
        print("  Ownership graph: %s nodes, %s edges" % (own_data.get("nodes"), own_data.get("edges")))

        # Test sanctions
        sanctions_response = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels/9100000/sanctions');
                    const data = await r.json();
                    return JSON.stringify({
                        status: r.status,
                        matches: data.total_matches,
                        is_sanctioned: data.is_sanctioned,
                        highest_score: data.highest_score
                    });
                } catch(e) {
                    return JSON.stringify({error: e.message});
                }
            }
        """)
        sanc_data = json.loads(sanctions_response)
        print("  Sanctions: matches=%s, sanctioned=%s, highest_score=%s" % (
            sanc_data.get("matches"), sanc_data.get("is_sanctioned"), sanc_data.get("highest_score")
        ))

        # Test risk
        risk_response = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels/9100000/risk');
                    const data = await r.json();
                    return JSON.stringify({
                        status: r.status,
                        total_score: data.total_score,
                        risk_level: data.risk_level,
                        factors: data.factors ? data.factors.length : 0
                    });
                } catch(e) {
                    return JSON.stringify({error: e.message});
                }
            }
        """)
        risk_data = json.loads(risk_response)
        print("  Risk: score=%s, level=%s, factors=%s" % (
            risk_data.get("total_score"), risk_data.get("risk_level"), risk_data.get("factors")
        ))

        # ══════════════════════════════════════════════════════
        # TEST 6: Check WebSocket connectivity
        # ══════════════════════════════════════════════════════
        print("\n[TEST 6] Checking WebSocket connectivity...")
        ws_logs = [l for l in all_console if "WS" in l or "WebSocket" in l or "ws://" in l.lower()]
        for log in ws_logs:
            print("  %s" % log)
        ws_connected = any("Connected" in l for l in ws_logs)
        print("  WebSocket connected: %s" % ws_connected)

        # ══════════════════════════════════════════════════════
        # TEST 7: Check for failed network requests
        # ══════════════════════════════════════════════════════
        print("\n[TEST 7] Network error audit...")
        if network_errors:
            for err in network_errors:
                print("  FAILED REQUEST: %s" % err)
        else:
            print("  No failed network requests (all 2xx/3xx)")

        # ══════════════════════════════════════════════════════
        # TEST 8: Full page screenshot at higher resolution
        # ══════════════════════════════════════════════════════
        print("\n[TEST 8] Capturing final full-page screenshot...")
        # Reset view: close panels, go back to map
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        await page.keyboard.press("Escape")
        await asyncio.sleep(1)

        final_path = os.path.join(SCREENSHOT_DIR, "05_final_state.png")
        await page.screenshot(path=final_path, full_page=False)
        print("  Screenshot: 05_final_state.png")

        # Copy key screenshots to brain dir for artifact display
        import shutil
        for fname in ["01_initial_load.png", "03_search.png", "04_sidebar.png", "05_final_state.png"]:
            src = os.path.join(SCREENSHOT_DIR, fname)
            dst = os.path.join(BRAIN_DIR, fname)
            if os.path.exists(src):
                shutil.copyfile(src, dst)

        await browser.close()

    # ══════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)
    print("Console errors:       %d" % len(console_errors))
    print("Uncaught page errors: %d" % len(page_errors))
    print("Failed HTTP requests: %d" % len(network_errors))
    print("Console warnings:     %d" % len(warnings))

    if console_errors:
        print("\n-- Console Errors --")
        for e in console_errors:
            print("  %s" % e)

    if page_errors:
        print("\n-- Page Errors --")
        for e in page_errors:
            print("  %s" % e)

    if network_errors:
        print("\n-- Failed Network Requests --")
        for e in network_errors:
            print("  %s" % e)

    if warnings:
        print("\n-- Warnings --")
        for w in warnings:
            print("  %s" % w)

    total_issues = len(console_errors) + len(page_errors) + len(network_errors)
    if total_issues == 0:
        print("\nSTATUS: ALL TESTS PASSED")
    else:
        print("\nSTATUS: %d ISSUE(S) FOUND" % total_issues, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
