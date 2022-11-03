from setuptools import setup, find_packages

exec(open("pixl_ehr/_version.py").read())

setup(
    name="pixl_ehr",
    version=__version__,  # noqa: F821
    author="Tom Young",
    url="https://github.com/UCLH-DIF/PIXL",
    description="PIXL electronic health record extractor",
    packages=find_packages(
        exclude=["*tests", "*.tests.*"],
    ),
    python_requires=">=3.10",
)
