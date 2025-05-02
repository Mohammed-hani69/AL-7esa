import os
import sys
from app import app, db
from models import User, Role
from werkzeug.security import generate_password_hash

def create_admin_user(phone, password, name="Admin"):
    """
    Create an admin user with the given phone number and password
    """
    with app.app_context():
        # Check if the user already exists
        existing_user = User.query.filter_by(phone=phone).first()
        
        if existing_user:
            if existing_user.role == Role.ADMIN:
                print(f"Admin user with phone {phone} already exists.")
                return
            else:
                # Update existing user to admin
                existing_user.role = Role.ADMIN
                existing_user.set_password(password)
                db.session.commit()
                print(f"User with phone {phone} updated to admin role.")
                return
        
        # Create new admin user
        admin_user = User(
            name=name,
            phone=phone,
            role=Role.ADMIN,
            is_active=True
        )
        admin_user.set_password(password)
        
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"Admin user created successfully with phone: {phone}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <phone_number> <password> [name]")
        sys.exit(1)
    
    phone = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    create_admin_user(phone, password, name)