from kafka import KafkaConsumer as KC
import json
from datetime import datetime
from models.sensor_data import SensorData
from extensions import db

class KafkaConsumer:
    def __init__(self, topic='sensor_data', bootstrap_servers=['localhost:9092']):
        # Configure Kafka consumer with required settings
        kafka_config = {
            'bootstrap_servers': bootstrap_servers,
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
            'group_id': 'smart_home_group',
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000,
            'session_timeout_ms': 30000
        }
        
        self.consumer = KC(
            topic,
            **kafka_config
        )

    def process_messages(self):
        for message in self.consumer:
            try:
                data = message.value
                
                # Convert timestamp string to datetime if needed
                if isinstance(data['timestamp'], str):
                    timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                else:
                    timestamp = data['timestamp']
                
                # Convert build_date string to date if needed
                if isinstance(data['build_date'], str):
                    build_date = datetime.strptime(data['build_date'], '%Y-%m-%d').date()
                else:
                    build_date = data['build_date']
                
                sensor_data = SensorData(
                    address=data['address'],
                    postal_code=data['postal_code'],
                    city=data['city'],
                    timestamp=timestamp,
                    target_temp=data['target_temp'],
                    indoor_temp=data['indoor_temp'],
                    outdoor_temp=data['outdoor_temp'],
                    presence=data['presence'],
                    humidity=data['humidity'],
                    sunlight=data['sunlight'],
                    orientation=data['orientation'],
                    dpe_class=data['dpe_class'],
                    dpe_value=data['dpe_value'],
                    build_date=build_date,
                    surface_m2=data['surface_m2'],
                    surface_m3=data['surface_m3'],
                    power=data['power'],
                    heating_time=data['heating_time'],
                    room_count=data['room_count']
                )
                
                db.session.add(sensor_data)
                db.session.commit()
                print(f"Saved data for {sensor_data.address} at {sensor_data.timestamp}")
                
            except Exception as e:
                print(f"Error processing message: {e}")
                db.session.rollback()

    def close(self):
        self.consumer.close()
