from flask import Flask
from extensions import db
from utils.kafka_consumer import KafkaConsumer
import signal
import sys

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartlast.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def signal_handler(sig, frame):
    print('\nStopping consumer...')
    if 'consumer' in globals():
        consumer.close()
    sys.exit(0)

def main():
    # Create and configure the Flask app
    app = create_app()
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start the consumer
    global consumer
    consumer = KafkaConsumer()
    
    print("Starting Kafka consumer...")
    with app.app_context():
        consumer.process_messages()

if __name__ == "__main__":
    main()
