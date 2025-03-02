from celery import Celery
import os, uuid, requests
from PIL import Image
from io import BytesIO
from server.database import SessionLocal
from server.models import ImageData, Request
from server.utils import trigger_webhook

celery = Celery(
    'server',
    backend='rpc://',
    broker='pyamqp://guest@localhost//'
)

celery.conf.task_routes = {
    'server.celery_worker.process_images': {'queue': 'image_processing_queue'}
}

@celery.task
def process_images(request_id: str):
    print(f"Processing images for request_id: {request_id}")
    db = SessionLocal()
    images = db.query(ImageData).filter(ImageData.request_id == request_id).all()
    upload_folder = "processed_images"
    os.makedirs(upload_folder, exist_ok=True)
    
    for img in images:
        try:
            print(f"Downloading image from {img.input_url}")
            response = requests.get(img.input_url)
            image = Image.open(BytesIO(response.content))
            output_path = os.path.join(upload_folder, f"{uuid.uuid4()}.jpg")
            print(f"Compressing and saving image to {output_path}")
            image.save(output_path, "JPEG", quality=50)
            img.output_url = output_path
            img.status = "processed"
        except Exception as e:
            print(f"Failed to process image {img.input_url}: {e}")
            img.status = "failed"
        db.commit()
    
    req = db.query(Request).filter(Request.request_id == request_id).first()
    req.status = "completed" if all(img.status == "processed" for img in images) else "failed"
    db.commit()
    print(f"Final request status: {req.status}")
    if req.webhook_url:
        print("Triggering webhook...")
        trigger_webhook(req)
    trigger_webhook(req)
    db.close()
    print("Processing completed.")
