from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import Request, ImageData
from server.schemas import StatusResponse, ImageDataResponse
from server.celery_worker import process_images
import uuid, csv
import os

router = APIRouter()

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), webhook_url: str = None, db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file format")

    request_id = str(uuid.uuid4())
    new_request = Request(request_id=request_id, status="processing", webhook_url=webhook_url)
    db.add(new_request)
    db.commit()

    csv_data = file.file.read().decode("utf-8").splitlines()
    reader = csv.reader(csv_data)
    next(reader)
    
    for row in reader:
        serial_no, product_name, input_urls = row
        for url in input_urls.split(','):
            image_entry = ImageData(
                request_id=request_id,
                product_name=product_name.strip(),
                input_url=url.strip(),
                status="pending"
            )
            db.add(image_entry)
    db.commit()

    process_images.apply_async(args=[request_id])
    return {"request_id": request_id}

@router.get("/status/{request_id}")
async def check_status(request_id: str, db: Session = Depends(get_db)):
    req = db.query(Request).filter(Request.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Invalid request ID")

    images = db.query(ImageData).filter(ImageData.request_id == request_id).all()
    return StatusResponse(request_id=request_id, status=req.status, images=[ImageDataResponse(input_url=img.input_url, output_url=img.output_url, status=img.status) for img in images])
