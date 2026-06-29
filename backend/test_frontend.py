import asyncio
import sys
from playwright.async_api import async_playwright

async def main():
    print("Starting browser smoke test...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        console_errors = []
        page_errors = []

        # Handlers
        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
                print(f"[Console Error] {msg.text}", file=sys.stderr)
            else:
                print(f"[Console {msg.type.upper()}] {msg.text}")

        def handle_pageerror(err):
            page_errors.append(err.message)
            print(f"[Page Error] {err.message}", file=sys.stderr)

        # Register event listeners
        page.on("console", handle_console)
        page.on("pageerror", handle_pageerror)

        print("Navigating to http://localhost:5173...")
        try:
            await page.goto("http://localhost:5173", timeout=15000, wait_until="networkidle")
        except Exception as e:
            print(f"Navigation error: {e}", file=sys.stderr)

        print("Waiting 5 seconds for vessel telemetry and map rendering...")
        await asyncio.sleep(5)

        title = await page.title()
        print(f"Page Title: {title}")

        screenshot_path = r"C:\Users\KIIT0001\Desktop\portwatch\smoke_test_screenshot.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")

        # Also copy it to the brain folder so the parent UI can display it
        brain_screenshot_path = r"C:\Users\KIIT0001\.gemini\antigravity\brain\c847e326-efee-4258-b574-e133f8180834\smoke_test_screenshot.png"
        import shutil
        try:
            shutil.copyfile(screenshot_path, brain_screenshot_path)
            print(f"Screenshot copied to brain folder: {brain_screenshot_path}")
        except Exception as copy_err:
            print(f"Failed to copy screenshot to brain folder: {copy_err}")

        await browser.close()

        print("\n--- Smoke Test Results ---")
        print(f"Console Errors: {len(console_errors)}")
        print(f"Page (Uncaught) Errors: {len(page_errors)}")
        
        if console_errors or page_errors:
            print("STATUS: FAILED (errors detected)", file=sys.stderr)
            sys.exit(1)
        else:
            print("STATUS: PASSED")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
