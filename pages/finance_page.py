"""
pages/finance_page.py
=====================
ProjectCentral  — project tile selection after login
FinancePage     — Finance tab navigation and sidebar verification
"""

from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
import config


class ProjectCentral:

    def __init__(self, page: Page):
        self.page = page

    @property
    def project_central_title(self):
        """Lazy locator — resolved against current page state every time."""
        return self.page.get_by_role("button", name="Project Central")

    def is_project_central_is_visible(self) -> bool:
        try:
            expect(self.project_central_title).to_be_visible(
                timeout=config.DEFAULT_WAIT_TIMEOUT
            )
            self.page.wait_for_load_state("load")
            self.page.wait_for_load_state("networkidle")
            return True
        except PlaywrightTimeoutError as e:
            raise TimeoutError(
                f"Timeout waiting for Project Central to load: {e}"
            )
        except AssertionError as e:
            raise AssertionError(f"Project Central is not visible: {e}")
        except Exception as e:
            raise Exception(f"Error checking Project Central visibility: {e}")

    def select_project(self, project_name: str) -> None:
        if not project_name or not isinstance(project_name, str):
            raise ValueError("Project name must be a non-empty string")

        print(f"→ Selecting project '{project_name}'...")
        project_tile = self.page.locator("#projecttiles-1207").get_by_text(
            project_name
        )
        project_tile.dblclick()

        # Wait for navigation to complete
        self.page.wait_for_load_state("load")

        # Wait for zone loading spinner to disappear before checking tabs
        try:
            self.page.get_by_text("Zone Loading").wait_for(
                state="hidden", timeout=config.NAVIGATION_TIMEOUT
            )
        except Exception:
            pass  # Spinner never appeared or already gone

        # networkidle after zone loads (some apps keep long-polling)
        try:
            self.page.wait_for_load_state(
                "networkidle", timeout=config.NETWORK_IDLE_TIMEOUT
            )
        except PlaywrightTimeoutError:
            pass  # Acceptable — don't block on polling requests

        # Verify Finance tab is visible (flexible — ignores leading spaces)
        finance_tab = self.page.get_by_role("tab", name="FINANCE", exact=False)
        expect(finance_tab).to_be_visible(timeout=config.NAVIGATION_TIMEOUT)
        print(f"✓ Project '{project_name}' loaded — FINANCE tab visible")


class FinancePage:

    def __init__(self, page: Page):
        self.page = page

    def is_finance_mode_visible(self) -> bool:
        finance_tab = self.page.get_by_role("tab", name="FINANCE", exact=False)
        expect(finance_tab).to_be_visible(timeout=config.NAVIGATION_TIMEOUT)
        return True

    def select_finance_mode(self) -> None:
        finance_tab = self.page.get_by_role("tab", name="FINANCE", exact=False)
        finance_tab.click()

        # Wait for sidebar to fully render before returning
        expect(self.page.get_by_text("Budgets")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        print("✓ Finance tab clicked and sidebar loaded")

        # Store sidebar links for is_finance_page_visible()
        self.estimates_link        = self.page.get_by_text("Estimates")
        self.budgets_link          = self.page.get_by_text("Budgets")
        self.bids_link             = self.page.get_by_text("Bids")
        self.bid_responses_link    = self.page.get_by_text("Bid Responses")
        self.vendor_contracts_link = self.page.get_by_text("Vendor Contracts")
        self.client_contracts_link = self.page.get_by_text("Client Contracts")
        self.vendor_pay_app_link   = self.page.get_by_text("Vendor Pay App")
        self.client_pay_app_link   = self.page.get_by_text("Client Pay App")
        self.change_events_link    = self.page.get_by_text("Change Events")
        self.forecasts_link        = self.page.get_by_text("Forecasts")
        print("✓ All Finance mode elements verified successfully")

    def is_finance_page_visible(self) -> bool:
        for link in [
            self.estimates_link,
            self.budgets_link,
            self.bids_link,
            self.bid_responses_link,
            self.vendor_contracts_link,
            self.client_contracts_link,
            self.vendor_pay_app_link,
            self.client_pay_app_link,
            self.change_events_link,
            self.forecasts_link,
        ]:
            expect(link).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        return True