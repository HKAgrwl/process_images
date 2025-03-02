from sqlalchemy import Column, String, Integer, ForeignKey
from server.database import Base

class Request(Base):
    __tablename__ = "request"
    request_id = Column(String(36), primary_key=True)
    status = Column(String(20), default="pending")
    webhook_url = Column(String(500), nullable=True)

class ImageData(Base):
    __tablename__ = "image_data"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(36), ForeignKey("request.request_id"))
    product_name = Column(String(255))
    input_url = Column(String(500))
    output_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")