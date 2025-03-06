from datetime import datetime
from extensions import db

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(200), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    target_temp = db.Column(db.Float, nullable=False)  # Consigne Temperature
    indoor_temp = db.Column(db.Float, nullable=False)  # Temperature Interieure
    outdoor_temp = db.Column(db.Float, nullable=False)  # Temperature Exterieure
    presence = db.Column(db.Boolean, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    sunlight = db.Column(db.Float, nullable=False)  # Ensoleillement
    orientation = db.Column(db.String(10), nullable=False)
    dpe_class = db.Column(db.String(1), nullable=False)
    dpe_value = db.Column(db.Integer, nullable=False)
    build_date = db.Column(db.Date, nullable=False)
    surface_m2 = db.Column(db.Float, nullable=False)
    surface_m3 = db.Column(db.Float, nullable=False)
    power = db.Column(db.Float, nullable=False)  # Puissance
    heating_time = db.Column(db.Float, nullable=False)  # temps de chauffe
    room_count = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<SensorData {self.address} - {self.timestamp}>'
