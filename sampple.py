from flask import Flask, request, jsonify
import os
import uuid
import csv
from PIL import Image
import requests
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from pydantic import BaseModel
from typing import List, Optional

# Flask app setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///image_processing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'processed_images'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Celery setup
CELERY_QUEUE_NAME = "image_processing"

def make_celery(app):
    celery = Celery(
        'app',
        backend='rpc://',
        broker='pyamqp://guest@localhost//'
    )
    celery.conf.task_routes = {
        'app.process_images': {'queue': CELERY_QUEUE_NAME}
    }
    return celery

celery = make_celery(app)

# Database models
class Request(db.Model):
    request_id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(20), default='pending')
    webhook_url = db.Column(db.String(500), nullable=True)

class ImageData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(36), db.ForeignKey('request.request_id'))
    product_name = db.Column(db.String(255))
    input_url = db.Column(db.String(500))
    output_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='pending')

# Ensure database tables are created before the app starts
def initialize_database():
    with app.app_context():
        db.create_all()

initialize_database()

# Pydantic Schemas
class ImageDataResponse(BaseModel):
    input_url: str
    output_url: Optional[str]
    status: str

class StatusResponse(BaseModel):
    request_id: str
    status: str
    images: List[ImageDataResponse]

# Upload API
@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    webhook_url = request.form.get('webhook_url')
    request_id = str(uuid.uuid4())
    new_request = Request(request_id=request_id, status='processing', webhook_url=webhook_url)
    db.session.add(new_request)
    db.session.commit()
    
    csv_file = file.read().decode('utf-8').splitlines()
    reader = csv.reader(csv_file)
    next(reader)  # Skip header
    
    for row in reader:
        # This also validated the csv format
        serial_no, product_name, input_urls = row
        for url in input_urls.split(','):
            image_entry = ImageData(
                request_id=request_id,
                product_name=product_name.strip(),
                input_url=url.strip(),
                status='pending'
            )
            db.session.add(image_entry)
    
    db.session.commit()
    process_images.apply_async(args=[request_id], queue=CELERY_QUEUE_NAME)
    
    return jsonify({'request_id': request_id}), 202

# Status API
@app.route('/status/<request_id>', methods=['GET'])
def check_status(request_id):
    req = Request.query.get(request_id)
    if not req:
        return jsonify({'error': 'Invalid request ID'}), 404
    
    images = ImageData.query.filter_by(request_id=request_id).all()
    response_data = StatusResponse(
        request_id=request_id,
        status=req.status,
        images=[
            ImageDataResponse(input_url=str(img.input_url), output_url=img.output_url, status=img.status)
            for img in images
        ]
    )
    
    return jsonify(response_data.model_dump(mode="json"))

@celery.task(queue=CELERY_QUEUE_NAME)
def process_images(request_id):
    print(f"[INFO] Processing images for request ID: {request_id}")
    with app.app_context():
        images = ImageData.query.filter_by(request_id=request_id).all()
        
        for img in images:
            try:
                print(f"[INFO] Downloading image from {img.input_url}")
                response = requests.get(img.input_url)
                image = Image.open(BytesIO(response.content))
                
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{uuid.uuid4()}.jpg')
                image.save(output_path, 'JPEG', quality=50)
                
                img.output_url = output_path
                img.status = 'processed'
                print(f"[SUCCESS] Processed image saved to {output_path}")
            except Exception as e:
                img.status = 'failed'
                print(f"[ERROR] Failed to process image {img.input_url}: {e}")
            
            db.session.commit()
        
        # Update request status
        req = Request.query.get(request_id)
        if all(img.status == 'processed' for img in images):
            req.status = 'completed'
            print(f"[SUCCESS] All images processed successfully for request ID: {request_id}")
            trigger_webhook(req)
        else:
            req.status = 'failed'
            print(f"[ERROR] Some images failed to process for request ID: {request_id}")
        db.session.commit()

def trigger_webhook(req):
    if req.webhook_url:
        payload = {
            'request_id': req.request_id,
            'status': req.status,
            'images': [
                {
                    'input_url': img.input_url,
                    'output_url': img.output_url,
                    'status': img.status
                } for img in ImageData.query.filter_by(request_id=req.request_id).all()
            ]
        }
        try:
            response = requests.post(req.webhook_url, json=payload)
            print(f"[INFO] Webhook triggered: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Failed to trigger webhook: {e}")

if __name__ == '__main__':
    app.run(debug=True)
