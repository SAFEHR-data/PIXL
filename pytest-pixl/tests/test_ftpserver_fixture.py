import pytest


@pytest.mark.pytester_example_path("tests/samples_for_fixture_tests/test_ftpserver_fixture")
def test_ftpserver_connection(pytester):
    """Test whether we can connect to the FTP server fixture"""
    pytester.copy_example("test_ftpserver_login.py")
    pytester.runpytest("-k", "test_ftpserver_login")
