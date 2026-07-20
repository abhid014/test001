"""
tests/test_finance_mode.py
==========================
Finance module end-to-end tests.
All settings (URLs, file paths, project name) come from config.py.
No allure, no PDF, no ZIP.
"""

import pytest
from pathlib import Path
from playwright.sync_api import Page

from pages.login_page import LoginPage
from pages.finance_page import ProjectCentral, FinancePage
from pages.finance_budgets_page import Budgets
from utils.excel_reader import read_excel_rows, read_project_name_from_row
from config import (
    EXCEL_FILE,
    FINANCE_SHEET,
    PROJECT_NAME_SHEET,
    PROJECT_NAME_ROW,
    PROJECT_NAME as DEFAULT_PROJECT,
)

# ── Test data ─────────────────────────────────────────────────────────────────
DATA_FILE    = Path(__file__).resolve().parents[1] / EXCEL_FILE
TEST_DATA    = read_excel_rows(str(DATA_FILE), FINANCE_SHEET)
PROJECT_NAME = read_project_name_from_row(
    str(DATA_FILE), row_number=PROJECT_NAME_ROW, sheet_name=PROJECT_NAME_SHEET
)


# ── Shared setup helpers ──────────────────────────────────────────────────────
def _validate(row: dict) -> tuple[str, str, str]:
    username     = row.get("username")
    password     = row.get("password")
    project_name = row.get("project_name") or PROJECT_NAME or DEFAULT_PROJECT
    assert username and password, "Missing username or password in Excel data"
    assert project_name,          "Missing project_name in Excel data or config.py"
    return username, password, project_name


def _login(page: Page, row: dict) -> None:
    username, password, _ = _validate(row)
    LoginPage(page).login(username, password)


def _select_project(page: Page, project_name: str) -> None:
    pc = ProjectCentral(page)
    assert pc.is_project_central_is_visible(), \
        "Project Central should be visible after login"
    pc.select_project(project_name)


def _setup_finance(page: Page, row: dict) -> FinancePage:
    """Login → select project → verify Finance tab → return FinancePage."""
    _, _, project_name = _validate(row)
    _login(page, row)
    _select_project(page, project_name)
    fp = FinancePage(page)
    assert fp.is_finance_mode_visible(), \
        "Finance tab should be visible after project selection"
    return fp


# ── TestFinanceMode ───────────────────────────────────────────────────────────
class TestFinanceMode:
    """Login, project selection, and Finance tab visibility."""

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_login(self, page: Page, row: dict) -> None:
        _login(page, row)

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_project_central(self, page: Page, row: dict) -> None:
        _, _, project_name = _validate(row)
        _login(page, row)
        _select_project(page, project_name)

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_finance_tab_visibility(self, page: Page, row: dict) -> None:
        _setup_finance(page, row)


# ── TestBudgets ───────────────────────────────────────────────────────────────
class TestBudgets:
    """Full Budget Room workflow: select → load → add → activate → line item."""

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_select_finance_mode(self, page: Page, row: dict) -> None:
        fp = _setup_finance(page, row)
        fp.select_finance_mode()
        assert fp.is_finance_page_visible(), \
            "Finance page elements should be visible after selecting Finance mode"

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_budgets_tile_load(self, page: Page, row: dict) -> None:
        fp = _setup_finance(page, row)
        fp.select_finance_mode()
        bp = Budgets(page)
        assert bp.is_budgets_tile_visible(), "Budgets tile should be visible"
        bp.load_budgets_tile()

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_add_budget_room(self, page: Page, row: dict) -> None:
        fp = _setup_finance(page, row)
        fp.select_finance_mode()
        bp = Budgets(page)
        assert bp.is_budgets_tile_visible(), "Budgets tile should be visible"
        bp.load_budgets_tile()
        budget_name = bp.add_budget_room()
        assert budget_name, "add_budget_room() returned None — all attempts exhausted"

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_activate_budget_room(self, page: Page, row: dict) -> None:
        fp = _setup_finance(page, row)
        fp.select_finance_mode()
        bp = Budgets(page)
        assert bp.is_budgets_tile_visible(), "Budgets tile should be visible"
        bp.load_budgets_tile()
        budget_name = bp.add_budget_room()
        assert budget_name, "add_budget_room() returned None"
        bp.activate_budget_room(budget_name)

    @pytest.mark.parametrize("row", TEST_DATA)
    def test_add_budget_line_item(self, page: Page, row: dict) -> None:
        fp = _setup_finance(page, row)
        fp.select_finance_mode()
        bp = Budgets(page)
        assert bp.is_budgets_tile_visible(), "Budgets tile should be visible"
        bp.load_budgets_tile()
        budget_name = bp.add_budget_room()
        assert budget_name, "add_budget_room() returned None"
        bp.activate_budget_room(budget_name)
        bp.add_budget_line_item(budget_name)