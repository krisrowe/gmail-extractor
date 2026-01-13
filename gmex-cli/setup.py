from setuptools import setup, find_packages

setup(
    name="gmex-cli",
    version="0.2.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click",
        "google-api-python-client",
        "google-auth",
        "google-auth-oauthlib",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "gmex=gmex_cli.cli:cli",
        ],
    },
)
