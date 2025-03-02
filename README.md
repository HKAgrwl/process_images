# FastAPI Image Processing System

## Overview
This is a FastAPI-based system that processes images asynchronously. Users upload a CSV file containing image URLs, and the system downloads, compresses, and stores them while updating their status in a PostgreSQL database. Celery is used for background task processing, and webhooks can be triggered upon completion, though they are optional.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install dependencies.

```bash
pip install -r requirements.txt
```

## Usage

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

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
