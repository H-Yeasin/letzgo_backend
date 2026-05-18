"""
Script to create or promote a user to admin.

Usage:
    python -m scripts.create_admin --phone +8801XXXXXXXXX
    python -m scripts.create_admin --phone +8801XXXXXXXXX --name "Admin Name"
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import SessionLocal
from app.models.user import User


def make_admin(phone: str, name: str = None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            print(f"User with phone {phone} not found.")
            print("Please register the user first via the mobile app.")
            return False

        user.is_admin = True
        if name:
            user.name = name
        db.commit()
        print(f"✅ User {user.name} ({user.phone}) is now an admin!")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--phone", required=True, help="Phone number of the user")
    parser.add_argument("--name", help="Name for the user")

    args = parser.parse_args()
    make_admin(args.phone, args.name)