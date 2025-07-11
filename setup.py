from setuptools import setup, find_packages

setup(
    name="syncbuddy",
    version="0.1.0",
    description="SyncBuddy makes it easy to sync files between two locations - securely handling sensitive data with automatic encryption and decryption.",
    author="Dominik Püllen",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=["pyyaml", 
    ],
    entry_points={
        "console_scripts": [
            "syncbuddy=syncbuddy.main:main", 
        ],
    },
    python_requires=">=3.7",
)
