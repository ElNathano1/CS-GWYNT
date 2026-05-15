from setuptools import setup, find_packages  # type: ignore

setup(
    name="cs-gwynt",
    version="0.1.0",
    description="Online Trading Card Game inspired by Gwent",
    author="CS-GWYNT Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi==0.111.1",
        "uvicorn==0.30.6",
        "pydantic==2.9.2",
        "sqlalchemy==2.0.35",
        "python-dotenv==1.0.1",
    ],
    extras_require={
        "dev": [
            "pytest==8.3.3",
            "pytest-asyncio==0.24.0",
        ],
    },
)
