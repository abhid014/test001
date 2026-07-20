# import openpyxl
# from pathlib import Path
# from typing import Any, Dict, List
# from playwright.sync_api import sync_playwright
# from pages.login_page import LoginPage


# def read_excel_rows(file_path: str, sheet_name: str) -> List[Dict[str, Any]]:
#     """Read the Excel sheet starting at row 2 and return rows as dicts."""
#     workbook = openpyxl.load_workbook(file_path, data_only=True)
#     try:
#         sheet = workbook[sheet_name]
#         headers = [header for header in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))]

#         data: List[Dict[str, Any]] = []
#         for row in sheet.iter_rows(min_row=2, values_only=True):
#             if not any(cell is not None for cell in row):
#                 continue

#             row_data = {}
#             for index, value in enumerate(row):
#                 header = headers[index] if index < len(headers) and headers[index] is not None else f"Column{index + 1}"
#                 row_data[header] = value
#             data.append(row_data)

#         return data
#     finally:
#         workbook.close()


# def main() -> None:
#     data_file = Path(__file__).resolve().parent / "test_data" / "test_automation_data.xlsx"
#     if not data_file.exists():
#         raise FileNotFoundError(f"Excel file not found: {data_file}")

#     rows = read_excel_rows(str(data_file), "LoginTests")
#     print(f"Found {len(rows)} rows from row 2 onward")

#     with sync_playwright() as playwright:
#         browser = playwright.chromium.launch(headless=False)
#         page = browser.new_page()

#         for row_index, row_data in enumerate(rows, start=2):
#             print(f"Row {row_index}:")
#             for header, value in row_data.items():
#                 print(f"  {header}: {value}")

#             username = row_data.get("username")
#             password = row_data.get("password")
#             if not username or not password:
#                 print("  Skipping row because username or password is missing")
#                 continue

#             page.goto("https://central.smartappqa.com/")
#             login_page = LoginPage(page)
#             login_page.login(username, password)
#             try:
#                 login_page.is_login_successful()
#                 print("  Login successful")
#                 login_page.logout()
#             except Exception as exc:
#                 print(f"  Login failed for row {row_index}: {exc}")
#             print()

#         browser.close()


# if __name__ == "__main__":
#     main()
