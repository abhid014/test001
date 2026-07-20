import pytest
from pathlib import Path
from playwright.sync_api import Page
from pages.login_page import LoginPage
from utils.excel_reader import read_excel_rows

DATA_FILE = Path(__file__).resolve().parents[1] / "test_data" / "test_automation_data.xlsx"
TEST_DATA = read_excel_rows(str(DATA_FILE), "LoginTests")

ALL_LOGIN_DATA = [
    {**row, "expected": row.get("expected", "success")} for row in TEST_DATA
]
@pytest.mark.skip
@pytest.mark.parametrize("row", ALL_LOGIN_DATA)
def test_login_logout(page: Page, row: dict) -> None:
    username = row.get("username")
    password = row.get("password")
    expected = row.get("expected", "success")
    
    try:
        assert username and password, "Missing username or password in login test data"
    except AssertionError as e:
        print(f"❌ Assertion Error: {e}")
        raise

    login_page = LoginPage(page)
    
    print(f"\n📝 Testing login for user: {username}")
    print(f"📝 Expected result: {expected.upper()}")
    
    try:
        login_page.login(username, password)
        print(f"✓ Login attempt completed for user: {username}")
    except Exception as e:
        print(f"❌ Login action failed with exception: {e}")
        raise

    if expected == "success":
        try:
            assert login_page.is_login_successful(), "Successful Login"
            print("✓ Login verification passed - User successfully logged in")
        except AssertionError as e:
            print(f"❌ Login verification failed: {e}")
            raise
        
        try:
            login_page.logout()
            print("✓ Logout action completed")
        except Exception as e:
            print(f"❌ Logout action failed: {e}")
            raise
        
        try:
            assert login_page.is_logout_successful(), "Successful Logout"
            print("✓ Logout verification passed - User successfully logged out")
        except AssertionError as e:
            print(f"❌ Logout verification failed: {e}")
            raise
    else:
        try:
            assert login_page.is_login_failed(), "Login Failed"
            print("⚠️ Login failure verified as expected - Invalid credentials correctly rejected")
        except AssertionError as e:
            print(f"❌ Expected login to fail but it succeeded: {e}")
            raise




