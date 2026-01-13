from setuptools import setup, find_packages

setup(
    name="gmex-sdk",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "email-archive",
        "google-api-python-client",
        "google-auth",
        "google-auth-oauthlib",
        "pyyaml"
    ],
)