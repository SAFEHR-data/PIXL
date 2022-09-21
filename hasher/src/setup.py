from setuptools import find_packages, setup

exec(open("hasher/_version.py").read())

setup(
    name="hasher",
    version=__version__,  # noqa: F821
    description="Service to securely hash identifiers",
    packages=find_packages(
        include=[
            "hasher*",
        ],
        exclude=[
            "*tests",
            "*.tests.*",
        ],
    ),
    python_requires=">=3.10",
)
