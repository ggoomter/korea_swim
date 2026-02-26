from playwright.sync_api import sync_playwright

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to home page...")
        page.goto("http://localhost:8000")

        # 1. Verify Loader appears (it might disappear fast, but let's check existence)
        print("Checking loader...")
        loader = page.locator("#loader")
        if loader.is_visible():
            print("Loader is visible initially.")

        # Wait for loader to hide (class 'hidden')
        print("Waiting for loader to hide...")
        try:
            page.wait_for_selector("#loader.hidden", timeout=10000)
            print("Loader hidden.")
        except Exception as e:
            print("Loader did not hide or error:", e)

        # 2. Check Title
        print(f"Page title: {page.title()}")
        assert "SwimSeoul" in page.title()

        # 3. Check Pool List (Desktop)
        print("Checking pool list...")
        page.wait_for_selector(".pool-card", timeout=5000)
        pools = page.locator(".pool-card").count()
        print(f"Found {pools} pool cards.")

        page.screenshot(path="verification/desktop_view.png")
        print("Desktop screenshot saved.")

        # 4. Mobile View Check
        print("Checking Mobile View...")
        page.set_viewport_size({"width": 375, "height": 667})
        page.reload()
        page.wait_for_selector("#loader.hidden", timeout=10000)

        # Check toggle button
        toggle_btn = page.locator("#mobile-toggle")
        if toggle_btn.is_visible():
            print("Mobile toggle button is visible.")
        else:
            print("Mobile toggle button NOT visible.")

        # Click toggle
        print("Clicking toggle...")
        toggle_btn.click()
        # Sidebar should hide, Map visible (or vice versa depending on logic)
        # My logic: Default list visible. Click -> Map visible (sidebar hidden).

        page.wait_for_timeout(500) # Wait for transition
        page.screenshot(path="verification/mobile_view_map.png")
        print("Mobile Map View screenshot saved.")

        toggle_btn.click()
        page.wait_for_timeout(500)
        page.screenshot(path="verification/mobile_view_list.png")
        print("Mobile List View screenshot saved.")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
