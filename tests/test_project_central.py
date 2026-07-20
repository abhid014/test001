import pytest
from unittest.mock import Mock, MagicMock, patch
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pages.finance_page import ProjectCentral

@pytest.mark.skip
class TestProjectCentral:
    """Test suite for ProjectCentral class with error handling."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright Page object."""
        return Mock(spec=Page)

    @pytest.fixture
    def project_central(self, mock_page):
        """Initialize ProjectCentral with mock page."""
        return ProjectCentral(mock_page)

    async def test_select_project_success(self, project_central, mock_page):
        """Test successful project selection."""
        try:
            await project_central.select_project("Test Project")
            mock_page.locator.assert_called_with("#projecttiles-1206")
            mock_page.wait_for_load_state.assert_called()
            print("✓ test_select_project_success passed")
        except Exception as e:
            pytest.fail(f"test_select_project_success failed: {str(e)}")

    async def test_select_project_element_not_found(self, project_central, mock_page):
        """Test project selection when element is not found."""
        try:
            mock_page.locator.side_effect = Exception("Element not found")
            with pytest.raises(Exception):
                await project_central.select_project("NonExistent Project")
            print("✓ test_select_project_element_not_found passed")
        except AssertionError as e:
            pytest.fail(f"test_select_project_element_not_found failed: {str(e)}")

    async def test_select_project_timeout(self, project_central, mock_page):
        """Test project selection with timeout error."""
        try:
            mock_page.wait_for_load_state.side_effect = PlaywrightTimeoutError("Navigation timeout")
            with pytest.raises(PlaywrightTimeoutError):
                await project_central.select_project("Test Project")
            print("✓ test_select_project_timeout passed")
        except AssertionError as e:
            pytest.fail(f"test_select_project_timeout failed: {str(e)}")

    async def test_is_project_central_visible_success(self, project_central, mock_page):
        """Test successful visibility check of Project Central."""
        try:
            result = await project_central.is_project_central_is_visible()
            assert result is True, "Expected True for visible element"
            mock_page.wait_for_load_state.assert_called()
            print("✓ test_is_project_central_visible_success passed")
        except Exception as e:
            pytest.fail(f"test_is_project_central_visible_success failed: {str(e)}")

    async def test_is_project_central_not_visible(self, project_central, mock_page):
        """Test when Project Central element is not visible."""
        try:
            with patch('pages.finance_page.expect') as mock_expect:
                mock_expect.side_effect = AssertionError("Element is not visible")
                with pytest.raises(AssertionError):
                    await   project_central.is_project_central_is_visible()
            print("✓ test_is_project_central_not_visible passed")
        except AssertionError as e:
            pytest.fail(f"test_is_project_central_not_visible failed: {str(e)}")

    async def test_project_central_initialization(self, mock_page):
        """Test ProjectCentral initialization."""
        try:
            mock_page.get_by_role.return_value = MagicMock()
            project_central = ProjectCentral(mock_page)
            assert project_central.page is mock_page, "Page not properly initialized"
            mock_page.get_by_role.assert_called_with("button", name="Project Central")
            print("✓ test_project_central_initialization passed")
        except Exception as e:
            pytest.fail(f"test_project_central_initialization failed: {str(e)}")

    async def test_select_project_with_invalid_project_name(self, project_central, mock_page):
        """Test project selection with empty or invalid project name."""
        try:
            mock_page.locator.return_value.get_by_text.return_value.click.side_effect = ValueError("Invalid project name")
            with pytest.raises(ValueError):
                await project_central.select_project("")
            print("✓ test_select_project_with_invalid_project_name passed")
        except AssertionError as e:
            pytest.fail(f"test_select_project_with_invalid_project_name failed: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
