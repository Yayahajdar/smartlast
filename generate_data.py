import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_building_data(num_buildings=10, days=7):
    # Generate timestamps for the past week at 5-minute intervals
    timestamps = [datetime.now() - timedelta(days=days) + timedelta(minutes=i*5) 
                 for i in range(int(days*24*60/5))]
    
    # Building base data
    buildings = []
    for i in range(num_buildings):
        building = {
            'address': f'Rue {i+1}',
            'postal_code': f'7500{i%9}',
            'city': 'Paris',
            'orientation': np.random.choice(['N', 'S', 'E', 'W']),
            'dpe_class': np.random.choice(['A', 'B', 'C', 'D']),
            'dpe_value': np.random.randint(50, 250),
            'build_date': datetime(np.random.randint(1950, 2020), 1, 1),
            'surface_m2': np.random.randint(50, 200),
            'surface_m3': np.random.randint(150, 600),
            'room_count': np.random.randint(2, 6)
        }
        buildings.append(building)

    # Generate time series data for each building
    data = []
    for building in buildings:
        for ts in timestamps:
            # Base temperature pattern with daily cycle
            hour = ts.hour
            base_temp = 20 + 2 * np.sin(2 * np.pi * (hour - 14) / 24)  # Peak at 2 PM
            
            # Add some noise
            indoor_temp = base_temp + np.random.normal(0, 0.5)
            outdoor_temp = base_temp - 5 + np.random.normal(0, 2)
            
            # Presence more likely during evening hours
            presence = bool(np.random.random() < 0.8 if 17 <= hour <= 23 else 0.3)
            
            # Sunlight hours (peaked during midday)
            sunlight = max(0, 5 * np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0
            
            # Power usage based on presence and temperature difference
            power = np.random.normal(1000, 100) if presence else np.random.normal(200, 50)
            
            # Heating time proportional to temperature difference when heating is needed
            heating_time = max(0, (20 - indoor_temp) * 2) if indoor_temp < 20 else 0
            
            record = {
                **building,
                'Datetime': ts,
                'target_temp': 20.0,
                'indoor_temp': indoor_temp,
                'outdoor_temp': outdoor_temp,
                'presence': presence,
                'humidity': np.random.normal(50, 5),
                'sunlight': sunlight,
                'power': power,
                'heating_time': heating_time
            }
            data.append(record)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Rename columns to match expected format
    column_mapping = {
        'Datetime': 'Datetime',
        'target_temp': 'Consigne Température (°C)',
        'indoor_temp': 'Température Intérieure (°C)',
        'outdoor_temp': 'Température Extérieure (°C)',
        'presence': 'Présence',
        'humidity': 'Humidité (%)',
        'sunlight': 'Ensoleillement (h)',
        'orientation': 'Orientation',
        'dpe_class': 'DPE Classe',
        'dpe_value': 'DPE Valeur',
        'build_date': 'Année de fabrication',
        'surface_m2': 'Surface (m²)',
        'surface_m3': 'Surface (m³)',
        'power': 'Puissance',
        'heating_time': 'temps de chauffe',
        'room_count': 'Nombre de pièces'
    }
    df = df.rename(columns=column_mapping)
    
    return df

if __name__ == '__main__':
    print("Generating building data...")
    df = generate_building_data(num_buildings=10, days=7)
    
    # Save to CSV
    output_file = 'simulation_donnees_batiments_nombre_pieces.csv'
    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")
    print(f"Generated {len(df)} records for {df['address'].nunique()} buildings")
