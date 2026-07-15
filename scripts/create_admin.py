"""
Script to create or promote a user to admin and set their dashboard password.

Usage:
    python -m scripts.create_admin --phone +8801XXXXXXXXX --password "secret"
    python -m scripts.create_admin --phone +8801XXXXXXXXX --name "Admin Name" --password "secret"
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password
from app.services.user_service import normalize_bd_phone


def make_admin(phone: str, name: str = None, password: str = None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == normalize_bd_phone(phone)).first()
        if not user:
            print(f"User with phone {phone} not found.")
            print("Please register the user first via the mobile app.")
            return False

        user.is_admin = True
        if name:
            user.name = name
        if password:
            user.password_hash = hash_password(password)
        db.commit()
        print(f"✅ User {user.name} ({user.phone}) is now an admin!")
        if password:
            print("✅ Dashboard password set.")
        elif not user.password_hash:
            print("⚠️  No password set — this admin cannot log in to the dashboard.")
            print("   Re-run with --password to set one.")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--phone", required=True, help="Phone number of the user")
    parser.add_argument("--name", help="Name for the user")
    parser.add_argument("--password", help="Dashboard login password for the admin")

    args = parser.parse_args()
    make_admin(args.phone, args.name, args.password)
