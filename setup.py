from setuptools import setup, find_packages

setup(
    name="cs-gwynt",
    version="0.1.0",
    description="Online Trading Card Game inspired by Gwent",
    author="CS-GWYNT Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "pydantic==2.5.0",
        "sqlalchemy==2.0.23",
        "python-dotenv==1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "pytest-asyncio==0.21.1",
        ],
    },
)
