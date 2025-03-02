from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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

def initialize_database(app):
    with app.app_context():
        db.create_all()
