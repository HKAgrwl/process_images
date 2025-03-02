import requests
from server.database import SessionLocal
from server.models import ImageData, Request

# Our webhook function
def trigger_webhook(req):
    if req.webhook_url:
        print(f"Triggering webhook for request_id: {req.request_id}")
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
            print(f"Webhook triggered successfully, response status: {response.status_code}")
        except Exception as e:
            print(f"Failed to trigger webhook: {e}")
        db.close()