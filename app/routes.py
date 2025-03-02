from flask import APIRouter, request, jsonify
import uuid
import csv
from app.database import db, Request, ImageData
from app.schemas import StatusResponse, ImageDataResponse
from app.core import celery
from app.core.tasks import process_images

file_router = APIRouter()

# Upload API
@file_router.post('/upload')
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    webhook_url = request.form.get('webhook_url', '')  # Handle missing webhook URL
    request_id = str(uuid.uuid4())

    # Create new request entry
    new_request = Request(request_id=request_id, status='processing', webhook_url=webhook_url)
    db.session.add(new_request)
    db.session.commit()

    try:
        csv_file = file.read().decode('utf-8').splitlines()
        reader = csv.reader(csv_file)
        headers = next(reader, None)  # Skip header, handle empty file

        if not headers or len(headers) < 3:
            return jsonify({'error': 'Invalid CSV format'}), 400

        for row in reader:
            if len(row) < 3:
                continue  # Skip malformed rows
            serial_no, product_name, input_urls = row[:3]

            for url in input_urls.split(','):
                image_entry = ImageData(
                    request_id=request_id,
                    product_name=product_name.strip(),
                    input_url=url.strip(),
                    status='pending'
                )
                db.session.add(image_entry)

        db.session.commit()
        process_images.apply_async(args=[request_id], queue="image_processing")

        return jsonify({'request_id': request_id}), 202

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process CSV: {str(e)}'}), 500

# Status API
@file_router.route('/status/<request_id>', methods=['GET'])
def check_status(request_id):
    req = Request.query.get(request_id)
    if not req:
        return jsonify({'error': 'Invalid request ID'}), 404

    images = ImageData.query.filter_by(request_id=request_id).all()
    
    response_data = StatusResponse(
        request_id=request_id,
        status=req.status,
        images=[
            ImageDataResponse(
                input_url=img.input_url, 
                output_url=img.output_url, 
                status=img.status
            ) for img in images
        ]
    )

    return jsonify(response_data.model_dump())
