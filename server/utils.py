import requests
from server.database import SessionLocal
from server.models import ImageData, Request

def trigger_webhook(req):
    if req.webhook_url:
        db = SessionLocal()
        payload = {
            'request_id': req.request_id,
            'status': req.status,
            'images': [
                {
                    'input_url': img.input_url,
                    'output_url': img.output_url,
                    'status': img.status
                } for img in db.query(ImageData).filter(ImageData.request_id == req.request_id).all()
            ]
        }
        try:
            requests.post(req.webhook_url, json=payload)
        except:
            pass
        db.close()