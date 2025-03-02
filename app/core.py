from flask import Flask, request, jsonify
import os
import uuid
import csv
from PIL import Image
import requests
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
from celery import Celery

from app.database import db, Request, ImageData, initialize_database
from app.schemas import StatusResponse, ImageDataResponse
from app.routes import file_router

# Flask app setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///image_processing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'processed_images'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
initialize_database(app)
app.include_router(app.include_router(file_router))

# Celery setup
CELERY_QUEUE_NAME = "image_processing"

def make_celery(app):
    celery = Celery(
        'app',
        backend='rpc://',
        broker='pyamqp://guest@localhost//'
    )
    celery.conf.task_routes = {
        'app.core.process_images': {'queue': CELERY_QUEUE_NAME}
    }
    return celery

celery = make_celery(app)



@celery.task(name="app.process_images", queue=CELERY_QUEUE_NAME)
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
