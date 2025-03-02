from pydantic import BaseModel
from typing import List, Optional

class ImageDataResponse(BaseModel):
    input_url: str
    output_url: Optional[str]
    status: str

class StatusResponse(BaseModel):
    request_id: str
    status: str
    images: List[ImageDataResponse]