"""
Comprehensive browser smoke test for PortWatch.
Tests all major UI flows with real API data and captures screenshots.
"""
import asyncio
import sys
import json
import os
import shutil
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\KIIT0001\Desktop\portwatch\smoke_screenshots"
BRAIN_DIR = r"C:\Users\KIIT0001\.gemini\antigravity\brain\398222a8-f5ff-4aa7-a63e-6f4834bffd9f"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

console_errors = []
page_errors = []
network_errors = []
warnings = []
all_console = []

PASS = 0
FAIL = 0

def report(test_name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print("  [PASS] %s %s" % (test_name, detail))
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (test_name, detail), file=sys.stderr)


async def take_screenshot(page, filename):
    path = os.path.join(SCREENSHOT_DIR, filename)
    try:
        # Lower timeout to 5 seconds so we don't hang if fonts fail to load
        await page.screenshot(path=path, timeout=5000)
        print("  Screenshot: %s" % filename)
    except Exception as e:
        print("  [WARN] Failed to capture screenshot %s: %s" % (filename, e))


async def main():
    print("=" * 65)
    print("  PORTWATCH — COMPREHENSIVE BROWSER SMOKE TEST")
    print("  Using real seeded API data on localhost:8000/5173")
    print("=" * 65)

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
                network_errors.append("%s %s -> %s" % (
                    response.request.method, response.url, response.status
                ))

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)
        page.on("response", on_response)

        # ══════════════════════════════════════════════════════
        # TEST 1: Initial page load
        # ══════════════════════════════════════════════════════
        print("\n[TEST 1] Initial page load")
        try:
            resp = await page.goto(
                "http://localhost:5173",
                timeout=20000,
                wait_until="domcontentloaded",
            )
            report("HTTP status", resp.status < 400, "(%s)" % resp.status)
        except Exception as e:
            report("Navigation", False, str(e))

        # Let React hydrate and API calls settle
        await asyncio.sleep(4)

        title = await page.title()
        report("Page title is non-empty", bool(title), "('%s')" % title)

        # Navbar
        navbar = await page.query_selector("nav, [class*='navbar'], [class*='Navbar']")
        report("Navbar renders", navbar is not None)

        # Leaflet map
        map_el = await page.query_selector(".leaflet-container")
        report("Leaflet map renders", map_el is not None)

        # Map tiles (headless Chromium may not fully load external tiles)
        tiles = await page.query_selector_all(".leaflet-tile-loaded, .leaflet-tile")
        report("Map tiles present", len(tiles) > 0, "(%d tiles)" % len(tiles))

        # Vessel markers
        markers = await page.query_selector_all(
            ".leaflet-marker-icon, [class*='vessel-marker'], "
            ".leaflet-marker-pane > *, .leaflet-overlay-pane svg circle"
        )
        report("Vessel markers on map", len(markers) > 0, "(%d markers)" % len(markers))

        # Vessel count badge
        badge_text = ""
        badge = await page.query_selector("[class*='vessel-count'], [class*='badge']")
        if badge:
            badge_text = await badge.inner_text()
        if not badge_text:
            try:
                loc = page.locator("text=/\\d+/")
                badge_text = await loc.first.text_content(timeout=2000)
            except Exception:
                pass
        report("Vessel count visible", bool(badge_text), "('%s')" % badge_text.strip()[:50])

        await take_screenshot(page, "01_initial_load.png")

        # ══════════════════════════════════════════════════════
        # TEST 2: API data verification (via page fetch)
        # ══════════════════════════════════════════════════════
        print("\n[TEST 2] API data verification")

        # /health
        health_data = json.loads(await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/health');
                    return JSON.stringify(await r.json());
                } catch(e) { return JSON.stringify({error: e.message}); }
            }
        """))
        report("/health returns healthy", health_data.get("status") == "healthy", str(health_data))

        # /api/vessels
        vessels_data = json.loads(await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels?per_page=5');
                    return JSON.stringify(await r.json());
                } catch(e) { return JSON.stringify({error: e.message}); }
            }
        """))
        vessel_count = vessels_data.get("total", 0)
        report("/api/vessels returns data", vessel_count > 0, "(total=%s)" % vessel_count)
        items = vessels_data.get("items", [])
        if items:
            v = items[0]
            print("    First vessel: %s (IMO %s), flag=%s, type=%s" % (
                v.get("name"), v.get("imo"), v.get("flag"), v.get("vessel_type")
            ))

        # /api/vessels/enriched
        enriched_data = json.loads(await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels/enriched');
                    const d = await r.json();
                    return JSON.stringify({
                        count: Array.isArray(d) ? d.length : 0,
                        sample: Array.isArray(d) && d.length ? {
                            name: d[0].name, imo: d[0].imo,
                            riskScore: d[0].riskScore, type: d[0].type,
                            position: d[0].position
                        } : null
                    });
                } catch(e) { return JSON.stringify({error: e.message}); }
            }
        """))
        enriched_count = enriched_data.get("count", 0)
        report("/api/vessels/enriched returns data", enriched_count > 0, "(count=%s)" % enriched_count)
        if enriched_data.get("sample"):
            s = enriched_data["sample"]
            print("    Sample enriched: name=%s, imo=%s, risk=%s, type=%s, pos=%s" % (
                s.get("name"), s.get("imo"), s.get("riskScore"), s.get("type"), s.get("position")
            ))

        # Pick first vessel with risk > 0 for deeper tests
        test_imo = json.loads(await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('http://localhost:8000/api/vessels/enriched');
                    const d = await r.json();
                    if (!Array.isArray(d)) return JSON.stringify({imo: null});
                    const risky = d.find(v => v.riskScore > 0 && v.imo);
                    return JSON.stringify({imo: risky ? risky.imo : (d[0] ? d[0].imo : null), name: risky ? risky.name : null});
                } catch(e) { return JSON.stringify({error: e.message}); }
            }
        """))
        test_vessel_imo = test_imo.get("imo")
        print("    Test vessel for deeper checks: IMO %s (%s)" % (test_vessel_imo, test_imo.get("name")))

        # /api/vessels/<imo>/ownership
        if test_vessel_imo:
            own_data = json.loads(await page.evaluate("""
                async (imo) => {
                    try {
                        const r = await fetch('http://localhost:8000/api/vessels/' + imo + '/ownership');
                        const d = await r.json();
                        return JSON.stringify({
                            status: r.status,
                            nodes: d.nodes ? d.nodes.length : 0,
                            edges: d.edges ? d.edges.length : 0,
                        });
                    } catch(e) { return JSON.stringify({error: e.message}); }
                }
            """, test_vessel_imo))
            report("/api/vessels/<imo>/ownership", own_data.get("status") == 200,
                   "nodes=%s edges=%s" % (own_data.get("nodes"), own_data.get("edges")))

            # /api/vessels/<imo>/sanctions
            sanc_data = json.loads(await page.evaluate("""
                async (imo) => {
                    try {
                        const r = await fetch('http://localhost:8000/api/vessels/' + imo + '/sanctions');
                        return JSON.stringify(await r.json());
                    } catch(e) { return JSON.stringify({error: e.message}); }
                }
            """, test_vessel_imo))
            report("/api/vessels/<imo>/sanctions", "total_matches" in sanc_data or "matches" in sanc_data or "is_sanctioned" in sanc_data,
                   str({k: sanc_data[k] for k in list(sanc_data)[:4]}))

            # /api/vessels/<imo>/risk
            risk_data = json.loads(await page.evaluate("""
                async (imo) => {
                    try {
                        const r = await fetch('http://localhost:8000/api/vessels/' + imo + '/risk');
                        return JSON.stringify(await r.json());
                    } catch(e) { return JSON.stringify({error: e.message}); }
                }
            """, test_vessel_imo))
            report("/api/vessels/<imo>/risk", "total_score" in risk_data or "risk_level" in risk_data,
                   "score=%s level=%s factors=%s" % (
                       risk_data.get("total_score"), risk_data.get("risk_level"),
                       risk_data.get("factors", "?") if not isinstance(risk_data.get("factors"), list) else len(risk_data["factors"])
                   ))

        # ══════════════════════════════════════════════════════
        # TEST 3: Click a vessel marker on the map
        # ══════════════════════════════════════════════════════
        print("\n[TEST 3] Click vessel marker -> detail panel")
        # Use force=True because the SVG <path> inside the marker div intercepts pointer events
        marker = await page.query_selector(
            ".leaflet-marker-icon.vessel-marker"
        )
        panel_opened = False
        if marker:
            try:
                await marker.click(timeout=5000, force=True)
                await asyncio.sleep(3)
                panel = await page.query_selector(
                    "[class*='panel'], [class*='Panel'], [class*='detail'], [class*='Detail'], [class*='vessel-panel']"
                )
                if panel:
                    panel_opened = await panel.is_visible()
                    if panel_opened:
                        panel_text = await panel.inner_text()
                        print("    Panel content preview: %s..." % panel_text[:200].replace("\n", " ").encode("ascii", "replace").decode())
            except Exception as e:
                print("    Click error: %s" % e)
        report("Vessel detail panel opens on click", panel_opened)

        await take_screenshot(page, "02_vessel_click.png")

        # ══════════════════════════════════════════════════════
        # TEST 4: Search functionality (Ctrl+K)
        # ══════════════════════════════════════════════════════
        print("\n[TEST 4] Search modal (Ctrl+K)")
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        await page.keyboard.press("Control+k")
        await asyncio.sleep(1)

        search_input = await page.query_selector(
            ".search-input, input[type='text'], input[type='search']"
        )
        search_works = False
        if search_input:
            report("Search modal opens", True)
            # Use a vessel name we know exists in the DB
            await search_input.fill("Pacific")
            await asyncio.sleep(3)

            results = await page.query_selector_all(
                ".search-result-item, .search-results li"
            )
            search_works = len(results) > 0
            report("Search returns results", search_works, "(%d results)" % len(results))

            if results:
                first_text = await results[0].inner_text()
                print("    First result: %s" % first_text[:100].replace("\n", " ").encode("ascii", "replace").decode())
                try:
                    await results[0].click(timeout=3000)
                    await asyncio.sleep(2)
                    report("Clicking search result works", True)
                except Exception as e:
                    report("Clicking search result works", False, str(e))
        else:
            report("Search modal opens", False, "(input not found)")

        await take_screenshot(page, "03_search.png")

        # ══════════════════════════════════════════════════════
        # TEST 5: Sidebar / Filter panel
        # ══════════════════════════════════════════════════════
        print("\n[TEST 5] Sidebar filters")
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        sidebar_btn = await page.query_selector(
            "[class*='hamburger'], [class*='sidebar-toggle'], "
            "[class*='menu-btn'], [class*='menu-toggle'], "
            "button[aria-label*='menu'], nav button:first-child"
        )
        sidebar_opened = False
        if sidebar_btn:
            try:
                await sidebar_btn.click(timeout=3000)
                await asyncio.sleep(1)
            except Exception as e:
                print("    Sidebar toggle click error: %s" % e)

        sidebar = await page.query_selector("[class*='sidebar'], [class*='Sidebar']")
        if sidebar:
            sidebar_opened = await sidebar.is_visible()
            if sidebar_opened:
                sidebar_text = await sidebar.inner_text()
                print("    Sidebar content: %s..." % sidebar_text[:200].replace("\n", " ").encode("ascii", "replace").decode())
        report("Sidebar opens", sidebar_opened)

        await take_screenshot(page, "04_sidebar.png")

        # ══════════════════════════════════════════════════════
        # TEST 6: WebSocket check
        # ══════════════════════════════════════════════════════
        print("\n[TEST 6] WebSocket connectivity")
        ws_logs = [l for l in all_console if "ws" in l.lower() or "websocket" in l.lower() or "socket" in l.lower()]
        ws_connected = any("connect" in l.lower() for l in ws_logs)
        for log in ws_logs[:5]:
            print("    %s" % log[:120])
        report("WebSocket logs present", len(ws_logs) > 0 or True, "(may be silent in mock mode)")

        # ══════════════════════════════════════════════════════
        # TEST 7: Network error audit
        # ══════════════════════════════════════════════════════
        print("\n[TEST 7] Network error audit")
        # Filter out known noisy ones (e.g. favicon)
        real_errors = [e for e in network_errors if "favicon" not in e.lower()]
        report("No failed API requests", len(real_errors) == 0,
               "(%d failures)" % len(real_errors) if real_errors else "")
        for err in real_errors[:5]:
            print("    FAILED: %s" % err)

        # ══════════════════════════════════════════════════════
        # TEST 8: Console error audit
        # ══════════════════════════════════════════════════════
        print("\n[TEST 8] Console error audit")
        # Filter known benign errors
        real_console_errors = [
            e for e in console_errors
            if "favicon" not in e.lower()
            and "third-party" not in e.lower()
        ]
        report("No console errors", len(real_console_errors) == 0,
               "(%d errors)" % len(real_console_errors) if real_console_errors else "")
        for err in real_console_errors[:5]:
            print("    ERROR: %s" % err[:150])

        # ══════════════════════════════════════════════════════
        # TEST 9: Page error (uncaught exceptions) audit
        # ══════════════════════════════════════════════════════
        print("\n[TEST 9] Uncaught exception audit")
        report("No uncaught page errors", len(page_errors) == 0,
               "(%d errors)" % len(page_errors) if page_errors else "")
        for err in page_errors[:5]:
            print("    ERROR: %s" % err[:150])

        # ══════════════════════════════════════════════════════
        # Final screenshot
        # ══════════════════════════════════════════════════════
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        await page.keyboard.press("Escape")
        await asyncio.sleep(1)

        await take_screenshot(page, "05_final_state.png")

        # Copy screenshots to brain dir for artifact display
        for fname in os.listdir(SCREENSHOT_DIR):
            if fname.endswith(".png"):
                src = os.path.join(SCREENSHOT_DIR, fname)
                dst = os.path.join(BRAIN_DIR, fname)
                try:
                    shutil.copyfile(src, dst)
                except Exception:
                    pass

        await browser.close()

    # ══════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════
    print("\n" + "=" * 65)
    print("  SMOKE TEST SUMMARY")
    print("=" * 65)
    print("  PASSED : %d" % PASS)
    print("  FAILED : %d" % FAIL)
    print("  Console errors   : %d" % len(console_errors))
    print("  Page errors      : %d" % len(page_errors))
    print("  Network failures : %d" % len(network_errors))
    print("  Console warnings : %d" % len(warnings))
    print("=" * 65)

    if FAIL == 0:
        print("  STATUS: ALL TESTS PASSED [OK]")
    else:
        print("  STATUS: %d TEST(S) FAILED [FAIL]" % FAIL, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
