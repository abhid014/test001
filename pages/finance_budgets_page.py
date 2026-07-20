"""
pages/finance_budgets_page.py
==============================
Budgets page object — covers:
  - Tile visibility / loading
  - Budget room creation (auto-incremented name, duplicate detection)
  - Budget room selection
  - Budget room activation (signature + checkbox + submit)
  - Budget line item addition
"""

import time
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeoutError
import config


class Budgets:

    def __init__(self, page: Page):
        self.page = page

    # ── Tile ──────────────────────────────────────────────────────────────────
    def is_budgets_tile_visible(self) -> bool:
        self.budgets_tile = self.page.get_by_text("Budgets")
        expect(self.budgets_tile).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        return True

    def load_budgets_tile(self):
        self.budgets_tile = self.page.get_by_text("Budgets")
        expect(self.budgets_tile).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        time.sleep(10)   # ensure element is fully interactable before dblclick
        self.budgets_tile.dblclick()
        print("✓ Budgets tile clicked")
        self.budget_room_iframe = self.page.frame_locator(
            "iframe[src*='budget-room']"
        )
        time.sleep(5)    # allow iframe content to fully load
        print("✓ Budget Room iframe loaded")
        return self.budget_room_iframe

    # ── Budget room creation ──────────────────────────────────────────────────
    def add_budget_room(
        self,
        base_name: str = "Auto Budget",
        start: int = 1,
        max_attempts: int = 20,
    ) -> str | None:
        """
        Create a budget room with a unique auto-incremented name.
        Returns the created budget name, or None if all attempts are exhausted.
        """
        budget_frame = self.page.frame_locator("iframe[src*='budget-room']")
        budget_frame.get_by_role("button", name="Add").click()

        for attempt in range(start, start + max_attempts):
            budget_name = f"{base_name} {attempt}"
            time.sleep(2)   # wait for form input to be ready

            budget_frame.get_by_role(
                "textbox", name="Enter Name of the Budget"
            ).fill(budget_name)
            budget_frame.get_by_role(
                "textbox", name="Enter Description"
            ).fill("Auto-generated budget room")
            budget_frame.locator(
                ".MuiInputBase-root.MuiInput-root.MuiInput-underline"
                ".MuiInputBase-colorPrimary.MuiInputBase-fullWidth"
                ".MuiInputBase-adornedStart.MuiInputBase-adornedEnd"
            ).click()
            budget_frame.get_by_role("option", name="None").click()
            budget_frame.get_by_role("button", name="Save").click()
            time.sleep(1)

            if budget_frame.get_by_text("already").is_visible(timeout=3000):
                print(f"Budget room '{budget_name}' already exists, trying next...")
                continue

            expect(
                budget_frame.get_by_text("New Budget Room added")
            ).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
            print(f"✓ Created Budget Room '{budget_name}'")
            return budget_name

        print(f"⚠️  All {max_attempts} name attempts exhausted for '{base_name}'")
        return None

    # ── Budget room selection ─────────────────────────────────────────────────
    def select_budget_room(self, budget_name: str) -> bool:
        budget_frame = self.page.frame_locator("iframe[src*='budget-room']")

        expect(budget_frame.get_by_role("grid")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        budget_row = budget_frame.get_by_text(budget_name, exact=False)
        expect(budget_row).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)

        print(f"✓ Found Budget Room '{budget_name}'")
        budget_row.click()
        time.sleep(1)
        return True

    # ── Budget room activation ────────────────────────────────────────────────
    def activate_budget_room(self, budget_name: str) -> bool:
        """Select, activate, sign, and open the Budget Manager for a budget room."""
        budget_frame = self.page.frame_locator("iframe[src*='budget-room']")

        self.select_budget_room(budget_name)

        # Edit
        expect(budget_frame.get_by_role("button", name="Edit")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        budget_frame.get_by_role("button", name="Edit").click()
        time.sleep(1)

        # Activate
        expect(budget_frame.get_by_role("button", name="Activate")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        budget_frame.get_by_role("button", name="Activate").click()
        time.sleep(1)

        # Confirm
        expect(budget_frame.get_by_role("button", name="Yes")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        budget_frame.get_by_role("button", name="Yes").click()
        time.sleep(2)

        # Signature canvas
        canvas = budget_frame.locator("canvas")
        expect(canvas).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        canvas.click(position={"x": 271, "y": 52})
        time.sleep(0.5)
        canvas.click(position={"x": 221, "y": 53})
        time.sleep(0.5)
        canvas.click(position={"x": 207, "y": 97})
        time.sleep(0.5)
        canvas.click(position={"x": 363, "y": 95})
        time.sleep(1)

        # Confirmation checkbox
        checkbox = budget_frame.get_by_role("checkbox")
        expect(checkbox).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        checkbox.check()
        time.sleep(1)

        # Submit
        expect(budget_frame.get_by_role("button", name="SUBMIT")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        budget_frame.get_by_role("button", name="SUBMIT").click()
        time.sleep(3)

        # Verify Active status
        expect(
            budget_frame.locator("span").filter(has_text="Active")
        ).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        print(f"✓ Budget Room '{budget_name}' is now Active")

        # Close right pane
        expect(
            budget_frame.get_by_role("button", name="Close Right Pane")
        ).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        budget_frame.get_by_role("button", name="Close Right Pane").click()
        time.sleep(1)

        # Open Budget Manager
        budget_frame.get_by_text(budget_name, exact=False).dblclick()
        expect(budget_frame.get_by_text("Budget Manager")).to_be_visible(
            timeout=config.DEFAULT_WAIT_TIMEOUT
        )
        print(f"✓ Budget Manager opened for '{budget_name}'")
        time.sleep(5)
        return True

    # ── Budget line item ──────────────────────────────────────────────────────
    def add_budget_line_item(self, budget_name: str) -> None:
        """Add a line item to an activated budget room."""
        budget_frame = self.page.frame_locator("iframe[src*='budget-room']")
        box          = self.page.locator("#box-1732").content_frame

        # Description
        budget_frame.get_by_role("textbox", name="Enter Description").click()
        budget_frame.get_by_role("textbox", name="Enter Description").fill(
            "Budget Line Description added"
        )

        # Cost Code Segment
        box.get_by_text("Cost Code Segment*").click()
        box.get_by_role("combobox").first.click()
        box.get_by_role("textbox", name="Search").click()
        box.get_by_role("textbox", name="Search").fill("airports")
        box.get_by_role("option", name="General Contractor- Airports -").click()

        # Cost Type
        box.get_by_text("Cost Type*").click()
        box.get_by_role("combobox", name="Change Status to").first.click()
        box.get_by_text("E - Equipment").click()

        # Est. Start Date
        box.get_by_text("Est. Start Date").click()
        box.get_by_role("textbox", name="MM/DD/YYYY").first.click()
        box.get_by_text("11", exact=True).click()

        # Est. End Date
        box.get_by_text("Est. End Date").click()
        box.get_by_role("textbox", name="MM/DD/YYYY").nth(1).click()
        box.locator(".rmdp-arrow-container.rmdp-right").click()
        box.locator(".rmdp-arrow-container.rmdp-right").click()
        box.get_by_text("31", exact=True).click()

        # Curve
        box.get_by_text("Curve").click()
        box.get_by_role("combobox", name="Change Status to").nth(1).click()
        box.get_by_text("Back Loaded").click()

        # Budget Amount / Unit of Measure
        box.get_by_text("Budget Amount*").click()
        box.get_by_role("button").first.click()
        box.get_by_role("combobox", name="0.00").click()
        box.get_by_role("option", name="ea").click()

        box.get_by_text("Unit of Measure").click()
        box.get_by_role("combobox", name="0.00").click()
        box.get_by_role("option", name="ea").click()

        # Unit Quantity
        box.get_by_text("Unit Quantity").click()
        box.locator('input[name="quantity"]').click()
        box.locator('input[name="quantity"]').fill("100.00")

        # Unit Rate
        box.get_by_text("Unit Rate").click()
        box.locator('input[name="cost"]').click()
        box.locator('input[name="cost"]').fill("10.00")

        # Budget Amount heading
        box.get_by_text("Budget Amount", exact=True).click()
        box.get_by_role("heading", name="$").click()

        # Save line item
        box.get_by_role("button", name="Save").click()
        box.locator("#standard-basic").click()
        box.get_by_role("button", name="+ Add").click()

        # Verify
        expect(
            budget_frame.get_by_role("dialog").get_by_text("Added New Budget Item")
        ).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        expect(
            budget_frame.get_by_text("00276 - General Contractor-")
        ).to_be_visible(timeout=config.DEFAULT_WAIT_TIMEOUT)
        print(f"✓ Added budget line item for '{budget_name}'") 