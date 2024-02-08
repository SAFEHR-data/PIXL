import os
from pathlib import Path

pytest_plugins = ["pytester"]

TEST_DIR = Path(__file__).parent

os.environ["FTP_HOST"] = "localhost"
os.environ["FTP_USER_NAME"] = "pixl_user"
os.environ["FTP_USER_PASSWORD"] = "longpassword"  # noqa: S105 Hardcoding password
os.environ["FTP_PORT"] = "20021"
os.environ["FTP_CERT_FILE"] = f"{TEST_DIR}/ssl/localhost.crt"
os.environ["FTP_KEY_FILE"] = f"{TEST_DIR}/ssl/localhost.key"
