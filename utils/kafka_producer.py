from kafka import KafkaProducer
import json
import pandas as pd
from datetime import datetime
import time

class SmartHomeDataProducer:
    def __init__(self, bootstrap_servers=['localhost:9092']):
        # Configure Kafka producer with required settings
        kafka_config = {
            'bootstrap_servers': bootstrap_servers,
            'value_serializer': lambda x: json.dumps(x, default=str).encode('utf-8'),
            'acks': 'all',
            'retries': 3,
            'retry_backoff_ms': 1000
        }
        self.producer = KafkaProducer(**kafka_config)
    
    def read_csv_data(self, csv_path):
        """Read building data from CSV"""
        try:
            # Read CSV with proper date parsing
            df = pd.read_csv(csv_path, parse_dates=['Datetime', 'Année de fabrication'])
            
            # Rename columns to match our database schema
            column_mapping = {
                'Adresse': 'address',
                'Code Postal': 'postal_code',
                'Ville': 'city',
                'Datetime': 'timestamp',
                'Consigne Température (°C)': 'target_temp',
                'Température Intérieure (°C)': 'indoor_temp',
                'Température Extérieure (°C)': 'outdoor_temp',
                'Présence': 'presence',
                'Humidité (%)': 'humidity',
                'Ensoleillement (h)': 'sunlight',
                'Orientation': 'orientation',
                'DPE Classe': 'dpe_class',
                'DPE Valeur': 'dpe_value',
                'Année de fabrication': 'build_date',
                'Surface (m²)': 'surface_m2',
                'Surface (m³)': 'surface_m3',
                'Puissance': 'power',
                'temps de chauffe': 'heating_time',
                'Nombre de pièces': 'room_count'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Convert presence to boolean
            df['presence'] = df['presence'].astype(bool)
            
            # Convert build_date to date only
            df['build_date'] = df['build_date'].dt.date
            
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return []
    
    def send_to_kafka(self, data):
        """Send data to Kafka topic"""
        try:
            self.producer.send('sensor_data', data)
            self.producer.flush()
            return True
        except Exception as e:
            print(f"Error sending to Kafka: {e}")
            return False
    
    def simulate_continuous_data(self, csv_path, interval=5):
        """Continuously read and send data from CSV"""
        print("Starting data simulation...")
        data_records = self.read_csv_data(csv_path)
        
        if not data_records:
            print("No data to simulate!")
            return
        
        print(f"Loaded {len(data_records)} records from CSV")
        
        record_index = 0
        while True:
            try:
                # Get next record (cycling through the data)
                record = data_records[record_index]
                record_index = (record_index + 1) % len(data_records)
                
                # Send to Kafka
                if self.send_to_kafka(record):
                    print(f"Sent record for {record['address']} at {record['timestamp']}")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nStopping simulation...")
                break
            except Exception as e:
                print(f"Error in simulation: {e}")
                time.sleep(interval)
    
    def close(self):
        """Close the Kafka producer"""
        self.producer.close()
