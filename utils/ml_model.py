import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from datetime import datetime, timedelta
import os

class TemperaturePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = 'models/temp_predictor.joblib'
        self.scaler_path = 'models/scaler.joblib'
        
        # Create models directory if it doesn't exist
        os.makedirs('models', exist_ok=True)
    
    def prepare_features(self, df):
        # Extract time-based features
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        df['month'] = pd.to_datetime(df['timestamp']).dt.month
        
        # Select features for prediction
        features = [
            'outdoor_temp', 'humidity', 'sunlight', 'room_count',
            'surface_m2', 'surface_m3', 'power', 'hour', 'day_of_week',
            'month', 'dpe_value'
        ]
        
        return df[features]
    
    def train(self, data, n_estimators=100, max_depth=10, test_size=0.2):
        # Prepare features
        X = self.prepare_features(data)
        y = data['indoor_temp']
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model with parameters
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Make predictions
        y_pred = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Save model and scaler
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        
        # Calculate feature importance and sort by importance
        feature_importance = dict(zip(X.columns, self.model.feature_importances_))
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'mse': float(mse),  # Convert numpy types to Python types for JSON serialization
            'rmse': float(np.sqrt(mse)),
            'r2': float(r2),
            'feature_importance': feature_importance,
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }
    
    def predict(self, data):
        if self.model is None:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
            else:
                raise ValueError("Model not trained yet!")
        
        X = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_next_24h(self, current_data):
        """Predict temperatures for the next 24 hours"""
        predictions = []
        current_time = pd.to_datetime(current_data['timestamp'].iloc[-1])
        
        # Create 24 future timestamps
        for i in range(24):
            future_time = current_time + timedelta(hours=i+1)
            
            # Copy the last row for prediction
            future_data = current_data.iloc[[-1]].copy()
            future_data['timestamp'] = future_time
            
            # Predict temperature
            pred_temp = self.predict(future_data)[0]
            
            predictions.append({
                'timestamp': future_time,
                'predicted_temp': pred_temp
            })
        
        return pd.DataFrame(predictions)
