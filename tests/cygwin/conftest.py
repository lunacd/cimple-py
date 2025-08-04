import importlib.resources

import pytest

from cimple import common


@pytest.fixture(name="cygwin_release_content_side_effect")
def cygwin_release_content_side_effect_fixture():
    class MockResponse:
        def __init__(self, content: bytes):
            self.content = content
            self.status_code = 200
            self.ok = True

        @property
        def text(self):
            return self.content.decode("utf-8")

        def raise_for_status(self):
            if not self.ok:
                raise RuntimeError(f"HTTP error: {self.status_code}")

    class Mock404Response:
        def __init__(self):
            self.status_code = 404
            self.ok = False

    def mock_cygwin_release_content(*args):
        url: str = args[0]
        assert url.startswith(common.constants.cygwin_pkg_url), (
            "Unexpected access to non-Cygwin URL"
        )

        # Use data/cygwin directory to mock Cygwin repository files
        with importlib.resources.path("tests", "data/cygwin") as cygwin_data_root:
            relative_path = url[len(common.constants.cygwin_pkg_url) :].lstrip("/")
            mock_file_path = cygwin_data_root / relative_path
            if mock_file_path.exists():
                return MockResponse(mock_file_path.read_bytes())
            return Mock404Response()

    return mock_cygwin_release_content
