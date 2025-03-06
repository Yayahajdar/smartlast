import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from models.sensor_data import SensorData
from datetime import datetime, timedelta

class MLProcessor:
    def __init__(self):
        self.model = LinearRegression()
        
    def prepare_data(self):
        # Get last 24 hours of data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        data = SensorData.query.filter(
            SensorData.timestamp.between(start_time, end_time)
        ).all()
        
        df = pd.DataFrame([{
            'timestamp': d.timestamp.timestamp(),
            'temperature': d.temperature,
            'room_count': d.room_count
        } for d in data])
        
        return df
        
    def train_model(self):
        df = self.prepare_data()
        if len(df) < 2:
            return False
            
        X = df[['timestamp', 'room_count']]
        y = df['temperature']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        self.model.fit(X_train, y_train)
        return True
        
    def get_temperature_predictions(self):
        if not self.train_model():
            return []
            
        # Predict next 24 hours
        future_times = [
            (datetime.utcnow() + timedelta(hours=i)).timestamp()
            for i in range(24)
        ]
        
        # Get unique room counts from recent data
        df = self.prepare_data()
        room_counts = df['room_count'].unique()
        
        predictions = []
        for room_count in room_counts:
            future_data = np.array([[t, room_count] for t in future_times])
            temps = self.model.predict(future_data)
            
            predictions.append({
                'building_type': f'{room_count} rooms',
                'predictions': [
                    {
                        'timestamp': future_times[i],
                        'temperature': float(temps[i])
                    }
                    for i in range(len(temps))
                ]
            })
            
        return predictions
