# Installation Guide

## Prerequisites

- Python 3.11+
- pip or conda
- PostgreSQL (optional, for production)

## Backend Setup

### 1. Clone the repository

```bash
git clone https://github.com/ElNathano1/CS-GWYNT.git
cd CS-GWYNT
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your settings.

### 5. Run the backend

```bash
python backend/main.py
```

The API will be available at `http://localhost:8000`

## Frontend Setup

### 1. Navigate to frontend directory

```bash
cd frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Start development server

```bash
npm run dev
```

## Docker Setup

### Run with Docker Compose

```bash
docker-compose up --build
```

This will start:

- Backend API on `http://localhost:8000`
- PostgreSQL database on `localhost:5432`

## Running Tests

```bash
python -m pytest tests/
```

## Troubleshooting

### Port Already in Use

Change the port in `.env` or use:

```bash
python backend/main.py --port 8001
```

### Database Issues

Make sure PostgreSQL is running and connection string is correct in `.env`.
