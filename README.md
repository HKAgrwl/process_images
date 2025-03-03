# FastAPI Image Processing System

## Overview
This is a FastAPI-based system that processes images asynchronously. Users upload a CSV file containing image URLs, and the system downloads, compresses, and stores them while updating their status in a SQLite database. Celery is used for background task processing, and webhooks can be triggered upon completion, though they are optional.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install dependencies.

```bash
pip install -r requirements.txt
```

## Usage

### Initialize the database (only first time)
```bash
python -c "from server.database import initialize_database; initialize_database()"
```

### Start FastAPI Server
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Celery Worker
```bash
celery -A server.celery_worker worker --loglevel=info
```

### Start RabbitMQ
```bash
docker-compose up -d  # Start RabbitMQ using Docker Compose
```

## API Endpoints

### Upload CSV (`POST /upload`)

Uploads a CSV file containing image URLs for processing.

```bash
curl -X POST "http://localhost:8000/upload" \
     -F "file=@test.csv" \
     -F "webhook_url=https://example.com/webhook"
```

### Check Status (`GET /status/{request_id}`)

Fetches the processing status and image details for a given request ID.

```bash
curl -X GET "http://localhost:8000/status/{request_id}"
```

## License

[MIT](https://choosealicense.com/licenses/mit/)
