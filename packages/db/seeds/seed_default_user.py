import asyncio
from uuid import UUID
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from schemas import User

# Deterministic UUID for the default user
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

def seed_default_user():
    """
    Inserts a default user into the database for local development.
    Deterministic UUID ensures consistency across environments.
    """
    engine = create_engine("postgresql://rain:rain@localhost:5432/rain")
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        user = session.execute(select(User).where(User.id == DEFAULT_USER_ID)).scalar_one_or_none()
        if user:
            print("Default user already exists. Skipping.")
            return
        
        new_user = User(
            id=DEFAULT_USER_ID,
            username="rain_admin",
            email="admin@rain.local"
        )
        session.add(new_user)
        session.commit()
        print("Default user seeded successfully.")

if __name__ == "__main__":
    seed_default_user()
