from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DangerInfo(Base):
    __tablename__ = "danger_infos"

    id = Column(Integer, primary_key=True)
    source = Column(String)
    area_name = Column(String, index=True)
    mountain_name = Column(String, index=True)
    danger_type = Column(Text)
    description = Column(Text)
    reported_date = Column(DateTime, index=True)
    original_url = Column(String)
    created_at = Column(DateTime)
