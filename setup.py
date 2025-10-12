#!/usr/bin/env python3
"""
Setup script for OEWS Migration Application

This setup script provides package installation and CLI entry points
for the OEWS Excel to SQL Database Migration Application.
"""

from setuptools import setup, find_packages
import os
import sys

# Ensure we're using Python 3.10 or higher (constitutional requirement)
if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10 or higher is required")

# Read version from package
def get_version():
    """Extract version from package"""
    version_file = os.path.join(os.path.dirname(__file__), 'src', '__init__.py')
    if os.path.exists(version_file):
        with open(version_file) as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('=')[1].strip().strip('"\'')
    return "1.0.0"

# Read long description from README
def get_long_description():
    """Read long description from README file"""
    readme_file = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_file):
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "OEWS Excel to SQL Database Migration Application"

# Core dependencies (per constitutional requirements)
INSTALL_REQUIRES = [
    "pandas>=1.5.0",
    "openpyxl>=3.0.0",
    "sqlalchemy>=2.0.0",
    "click>=8.0.0",
    "python-dotenv>=0.19.0",
    "psycopg2-binary>=2.9.0",
    "alembic>=1.12.0",
    "tqdm>=4.65.0"
]

# Development dependencies
EXTRAS_REQUIRE = {
    'dev': [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "black>=23.0.0",
        "flake8>=6.0.0",
        "mypy>=1.0.0"
    ],
    'test': [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0"
    ]
}

setup(
    name="oews-migration",
    version=get_version(),
    description="OEWS Excel to SQL Database Migration Application",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="OEWS Migration Team",
    author_email="team@oews-migration.com",
    url="https://github.com/oews-migration/oews-migration",

    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,

    # Python version requirement (constitutional)
    python_requires=">=3.10",

    # Dependencies
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,

    # CLI entry points
    entry_points={
        'console_scripts': [
            'oews-migrate=cli.main:main',
            'oews-discover=cli.main:discover',
            'oews-analyze=cli.main:analyze',
            'oews-create-schema=cli.main:create_schema',
            'oews-validate=cli.main:validate',
            'oews-rollback=cli.main:rollback',
            'oews-status=cli.main:status',
        ],
    },

    # Package metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: Utilities",
    ],

    keywords=[
        "excel", "sql", "database", "migration", "etl",
        "oews", "data-processing", "cli", "pandas", "sqlalchemy"
    ],

    # Additional package data
    package_data={
        "": ["*.md", "*.txt", "*.yaml", "*.yml", "*.json"],
    },

    # Zip safe
    zip_safe=False,

    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/oews-migration/oews-migration/issues",
        "Documentation": "https://oews-migration.readthedocs.io/",
        "Source": "https://github.com/oews-migration/oews-migration",
    },
)