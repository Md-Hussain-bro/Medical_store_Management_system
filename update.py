from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Add is_active column if not exists
        db.session.execute(text('''
            ALTER TABLE medicines ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL
        '''))
        db.session.commit()
        print("Column 'is_active' added successfully!")
    except Exception as e:
        if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
            print("Column already exists, skipping...")
        else:
            print(f"Error: {e}")