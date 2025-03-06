from utils.kafka_producer import SmartHomeDataProducer
import os

def main():
    # Get the absolute path to the CSV file
    csv_path = os.path.join(os.path.dirname(__file__), 'simulation_donnees_batiments_nombre_pieces.csv')
    
    # Create and start the producer
    producer = SmartHomeDataProducer()
    try:
        # Start simulation with 5-second intervals
        producer.simulate_continuous_data(csv_path, interval=5)
    except KeyboardInterrupt:
        print("\nStopping simulation...")
    finally:
        producer.close()

if __name__ == "__main__":
    main()
