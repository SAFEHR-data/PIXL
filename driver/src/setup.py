from setuptools import setup, find_packages

exec(open("pixl_driver/_version.py").read())

setup(
    name="pixl_driver",
    version=__version__,  # noqa: F821
    packages=find_packages("."),
    author="Tom Young",
    url="https://github.com/UCLH-DIF/PIXL",
    entry_points={"console_scripts": ["pixl = pixl_driver.main:cli"]},
    description="Command line interaction with PIXL",
)
