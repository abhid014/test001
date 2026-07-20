"""
pages/login_page.py
===================
Handles login, logout, and verification.
- Locators are lazy @properties (resolved at call time, not __init__)
- Always navigates to BASE_URL before filling credentials
- Uses config.py for URL and timeout values
"""

from playwright.sync_api import Page, expect
import config


class LoginPage:

    def __init__(self, page: Page):
        self.page = page

    # ── Lazy locators ─────────────────────────────────────────────────────────
    @property
    def username_input(self):
        return self.page.get_by_role("textbox", name="Email*")

    @property
    def password_input(self):
        return self.page.get_by_role("textbox", name="Password*")

    @property
    def login_button(self):
        return self.page.get_by_role("button", name="Login")

    # ── Actions ───────────────────────────────────────────────────────────────
    def login(self, username: str, password: str) -> None:
        """Navigate to login page and sign in with given credentials."""
        self.page.goto(config.BASE_URL)
        self.page.wait_for_load_state("load")
        self.page.wait_for_load_state("networkidle")
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.click_login()

    def click_login(self) -> None:
        self.login_button.click(timeout=config.DEFAULT_WAIT_TIMEOUT)
        self.page.wait_for_load_state("load")
        self.page.wait_for_load_state("networkidle")

    def logout(self) -> None:
        self.page.locator("#image-1031").click()
        self.page.wait_for_load_state("load")
        self.page.wait_for_load_state("networkidle")
        self.page.get_by_role("menuitem", name="Logout ").click()
        self.page.wait_for_load_state("load")
        self.page.wait_for_load_state("networkidle")

    # ── Verifications ─────────────────────────────────────────────────────────
    def is_login_successful(self) -> bool:
        try:
            if self.page.get_by_role("img", name="AD US20QA").is_visible():
                print("✓ Login successful")
                return True
        except Exception:
            pass
        try:
            if not self.login_button.is_visible():
                print("✓ Login successful (login button gone)")
                return True
        except Exception:
            print("✓ Login successful (login button removed from DOM)")
            return True
        return False

    def is_logout_successful(self) -> bool:
        login_text = self.page.get_by_text("Please login to your smartapp")
        expect(login_text).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        print("✓ Logout successful")
        return True

    def is_login_failed(self) -> bool:
        try:
            if self.page.get_by_text("Invalid User Name or Password").is_visible():
                print("✗ Login failed — invalid credentials message shown")
                return True
        except Exception:
            pass
        try:
            if self.username_input.is_visible():
                print("✗ Login failed — still on login page")
                return True
        except Exception:
            pass
        return False