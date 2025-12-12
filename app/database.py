from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.danger import Base

DATABASE_URL = "postgresql://user:password@db:5432/trail_db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)