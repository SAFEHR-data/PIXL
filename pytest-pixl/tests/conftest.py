import os
from pathlib import Path

# Avoid running samples for fixture tests directly with pytest
collect_ignore = ["samples_for_fixture_tests"]

pytest_plugins = ["pytester"]

TEST_DIR = Path(__file__).parent

os.environ["FTP_HOST"] = "localhost"
os.environ["FTP_USER_NAME"] = "pixl_user"
os.environ["FTP_USER_PASSWORD"] = "longpassword"  # noqa: S105 Hardcoding password
os.environ["FTP_PORT"] = "20021"
