from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from extensions import db, login_manager
from utils.ml_model import TemperaturePredictor
from utils.kafka_producer import SmartHomeDataProducer
from utils.jeedom_client import JeedomClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///smartlast.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    settings = db.relationship('UserSettings', backref='user', lazy=True)

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_source = db.Column(db.String(20), default='csv')
    data_source_settings = db.Column(db.Text, nullable=True)
    ml_model_type = db.Column(db.String(20), default='random_forest')
    training_schedule = db.Column(db.String(20), default='manual')
    theme = db.Column(db.String(20), default='light')
    chart_interval = db.Column(db.Integer, default=5)
    temp_unit = db.Column(db.String(20), default='celsius')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', active_page='settings')

@app.route('/ml-training')
@login_required
def ml_training():
    return render_template('ml_training.html', active_page='ml_training')

@app.route('/data-simulation')
@login_required
def data_simulation():
    return render_template('data_simulation.html', active_page='data_simulation')

@app.route('/kafka-status')
@login_required
def kafka_status():
    return render_template('kafka_status.html', active_page='kafka_status')

@app.route('/jeedom')
@login_required
def jeedom():
    return render_template('jeedom.html', active_page='jeedom')

@app.route('/api/check-auth')
@login_required
def check_auth():
    return jsonify({'authenticated': True})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        
        # Create default settings for the user
        settings = UserSettings(
            user=user,
            data_source='csv',
            data_source_settings='{"path": "simulation_donnees_batiments_nombre_pieces.csv", "interval": 5}',
            ml_model_type='random_forest',
            training_schedule='manual',
            theme='light',
            chart_interval=5,
            temp_unit='celsius'
        )
        db.session.add(settings)
        
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    try:
        # Read CSV file using absolute path
        csv_path = os.path.join(os.path.dirname(__file__), 'simulation_donnees_batiments_nombre_pieces.csv')
        data = pd.read_csv(csv_path)
        data['Datetime'] = pd.to_datetime(data['Datetime'])
        
        # Prepare data for ML model
        ml_data = data.copy()
        ml_data = ml_data.rename(columns={
            'Datetime': 'timestamp',
            'Température Intérieure (°C)': 'indoor_temp',
            'Température Extérieure (°C)': 'outdoor_temp',
            'Humidité (%)': 'humidity',
            'Ensoleillement (h)': 'sunlight',
            'Surface (m²)': 'surface_m2',
            'Surface (m³)': 'surface_m3',
            'Puissance': 'power',
            'DPE Valeur': 'dpe_value',
            'Nombre de pièces': 'room_count'
        })
        
        # Initialize and train ML model
        predictor = TemperaturePredictor()
        ml_metrics = predictor.train(ml_data)
        
        # Get last 24 hours of data for display
        data = data.sort_values('Datetime').tail(288)  # Last 24 hours
        
        # Calculate metrics
        metrics = {
            'avg_temp': float(data['Température Intérieure (°C)'].mean()),
            'avg_humidity': float(data['Humidité (%)'].mean()),
            'energy_efficiency': float(100 - data['DPE Valeur'].mean() / 10),
            'model_accuracy': float(ml_metrics['r2'])
        }
        
        # Temperature data
        temp_data = {
            'timestamps': data['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'indoor_temps': data['Température Intérieure (°C)'].tolist(),
            'outdoor_temps': data['Température Extérieure (°C)'].tolist()
        }
        
        # Get ML predictions
        predictions = predictor.predict_next_24h(ml_data)
        pred_data = {
            'timestamps': [p['timestamp'].strftime('%Y-%m-%d %H:%M:%S') for p in predictions],
            'temperatures': [p['predicted_temp'] for p in predictions]
        }
        
        # Energy usage by room count
        energy_data = data.groupby('Nombre de pièces')['Puissance'].mean().reset_index()
        energy_usage = {
            'room_counts': energy_data['Nombre de pièces'].tolist(),
            'power_usage': energy_data['Puissance'].tolist()
        }
        
        response_data = {
            'metrics': metrics,
            'temperature_data': temp_data,
            'predictions': pred_data,
            'energy_data': energy_usage,
            'feature_importance': ml_metrics['feature_importance']
        }
        return jsonify(response_data)
        
    except Exception as e:
        print('Error:', str(e))
        return jsonify({
            'error': f'Error processing data: {str(e)}'
        })

# ML Training API
@app.route('/api/train-model', methods=['POST'])
@login_required
def train_model():
    try:
        data = request.get_json()
        predictor = TemperaturePredictor()
        
        # Get model parameters
        n_estimators = int(data.get('n_estimators', 100))
        max_depth = int(data.get('max_depth', 10))
        test_size = 1 - (float(data.get('train_split', 80)) / 100)
        
        # Read and prepare data
        csv_path = os.path.join(os.path.dirname(__file__), 'simulation_donnees_batiments_nombre_pieces.csv')
        df = pd.read_csv(csv_path)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'Datetime': 'timestamp',
            'Température Intérieure (°C)': 'indoor_temp',
            'Température Extérieure (°C)': 'outdoor_temp',
            'Humidité (%)': 'humidity',
            'Ensoleillement (h)': 'sunlight',
            'Surface (m²)': 'surface_m2',
            'Surface (m³)': 'surface_m3',
            'Puissance': 'power',
            'DPE Valeur': 'dpe_value',
            'Nombre de pièces': 'room_count'
        })
        
        # Train model with parameters
        metrics = predictor.train(df, n_estimators=n_estimators, max_depth=max_depth, test_size=test_size)
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        print('Error in train_model:', str(e))
        return jsonify({'error': str(e)})
@app.route('/api/test-prediction', methods=['POST'])
@login_required
def test_prediction():
    try:
        data = request.get_json()
        predictor = TemperaturePredictor()
        
        # Create a test dataframe with the input data
        test_data = pd.DataFrame([{
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'outdoor_temp': float(data.get('outdoor_temp', 20)),
            'humidity': float(data.get('humidity', 50)),
            'sunlight': float(data.get('sunlight', 5)),
            'room_count': int(data.get('room_count', 4)),
            'surface_m2': float(data.get('surface_m2', 100)),
            'surface_m3': float(data.get('surface_m3', 300)),
            'power': float(data.get('power', 1000)),
            'dpe_value': float(data.get('dpe_value', 200))
        }])
        
        # Make prediction
        prediction = predictor.predict(test_data)
        
        return jsonify({
            'success': True,
            'predicted_temp': float(prediction[0])
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Simulation API
@app.route('/api/start-simulation', methods=['POST'])
@login_required
def start_simulation():
    try:
        data = request.get_json()
        # Start simulation process
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/stop-simulation', methods=['POST'])
@login_required
def stop_simulation():
    try:
        # Stop simulation process
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/simulation-data')
@login_required
def get_simulation_data():
    try:
        # Get latest simulation data
        return jsonify({
            'progress': 50,
            'total_records': 100,
            'data': {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'temperature': 22.5,
                'humidity': 45.0,
                'power': 1000.0
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Kafka API
@app.route('/api/test-kafka-connection', methods=['POST'])
@login_required
def test_kafka_connection():
    try:
        # Test Kafka connection
        return jsonify({'connected': True})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

@app.route('/api/start-kafka-consumer', methods=['POST'])
@login_required
def start_kafka_consumer():
    try:
        # Start Kafka consumer
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/stop-kafka-consumer', methods=['POST'])
@login_required
def stop_kafka_consumer():
    try:
        # Stop Kafka consumer
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/reset-kafka-consumer', methods=['POST'])
@login_required
def reset_kafka_consumer():
    try:
        # Reset Kafka consumer offset
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/kafka-messages')
@login_required
def get_kafka_messages():
    try:
        # Get latest Kafka messages
        return jsonify({
            'messages': [{
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'building_id': 1,
                'temperature': 22.5,
                'humidity': 45.0,
                'power_usage': 1000.0
            }]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Settings API
@app.route('/api/get-settings')
@login_required
def get_settings():
    try:
        return jsonify({
            'data_source': {
                'source': 'csv',
                'settings': {
                    'path': 'simulation_donnees_batiments_nombre_pieces.csv',
                    'interval': 5
                }
            },
            'ml_settings': {
                'model_type': 'random_forest',
                'training_schedule': 'manual',
                'model_path': 'models/'
            },
            'display_settings': {
                'theme': 'light',
                'chart_interval': 5,
                'temp_unit': 'celsius'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/save-data-source-settings', methods=['POST'])
@login_required
def save_data_source_settings():
    try:
        data = request.get_json()
        # Save data source settings
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/save-ml-settings', methods=['POST'])
@login_required
def save_ml_settings():
    try:
        data = request.get_json()
        # Save ML settings
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/save-display-settings', methods=['POST'])
@login_required
def save_display_settings():
    try:
        data = request.get_json()
        # Save display settings
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/update-password', methods=['POST'])
@login_required
def update_password():
    try:
        data = request.get_json()
        user = User.query.get(current_user.id)
        user.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

# Jeedom API
@app.route('/api/jeedom/devices', methods=['GET'])
@login_required
def get_jeedom_devices():
    try:
        client = JeedomClient()
        data = client.get_full_data()
        print("Jeedom data received:", data)  # Debug print
        return jsonify(data)
    except Exception as e:
        print("Error in get_jeedom_devices:", str(e))  # Debug print
        return jsonify({'error': str(e)}), 500

@app.route('/api/jeedom/device/<device_id>', methods=['GET'])
@login_required
def get_jeedom_device(device_id):
    try:
        client = JeedomClient()
        device = client.get_device_info(device_id)
        if device is None:
            return jsonify({'error': 'Device not found'}), 404
        return jsonify(device)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/jeedom/command/<cmd_id>/history', methods=['GET'])
@login_required
def get_command_history(cmd_id):
    try:
        # First validate the command exists
        client = JeedomClient()
        cmd_info = client.get_command_info(cmd_id)
        
        if not cmd_info or not isinstance(cmd_info, dict):
            return jsonify({
                'error': f'Command {cmd_id} not found or invalid response',
                'suggestion': 'Please verify the command ID in Jeedom'
            }), 404
        
        command_name = cmd_info.get('name', 'Unknown Command')
        
        # Check if history logging is enabled
        if 'isHistorized' in cmd_info and not cmd_info['isHistorized']:
            return jsonify({
                'error': 'History logging is disabled for this command',
                'command_name': command_name,
                'suggestion': 'Enable history logging in Jeedom for this command'
            }), 400
        
        # Get the history
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        print(f"Getting history for command {cmd_id} ({command_name})")  # Debug print
        print(f"Date range: {start_date} to {end_date}")  # Debug print
        
        history = client.get_command_history(cmd_id, start_date, end_date)
        
        print(f"Received history data: {history}")  # Debug print
        
        if not history:
            return jsonify({
                'error': 'No history data available for this command in the selected time range',
                'command_name': command_name,
                'suggestion': 'Verify the command has recorded data in Jeedom for this period'
            }), 404
            
        return jsonify(history)
    except Exception as e:
        print(f"Error in get_command_history: {str(e)}")  # Debug print
        import traceback
        print(traceback.format_exc())  # Debug print stack trace
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
