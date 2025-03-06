from app import app, db, User, UserSettings
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            
            # Create default settings for admin
            settings = UserSettings(
                user=admin,
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
            print("Created admin user with default settings")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    init_db()
