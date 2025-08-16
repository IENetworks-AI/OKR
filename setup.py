from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="okr-project",
    version="0.1.0",
    author="OKR Project Team",
    author_email="team@okr-project.com",
    description="Professional repository for AI and Data Engineering teams collaboration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/okr-project",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.1",
            "isort>=5.12.0",
            "pre-commit>=3.3.3",
        ],
        "ai": [
            "torch>=2.0.1",
            "tensorflow>=2.13.0",
            "transformers>=4.31.0",
            "scikit-learn>=1.3.0",
        ],
        "data": [
            "apache-airflow>=2.6.3",
            "kafka-python>=2.0.2",
            "sqlalchemy>=2.0.19",
            "psycopg2-binary>=2.9.7",
        ],
    },
    entry_points={
        "console_scripts": [
            "okr-ai-api=ai.src.inference.main:main",
            "okr-data-processor=data.scripts.processor:main",
            "okr-setup=shared.utils.setup:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)