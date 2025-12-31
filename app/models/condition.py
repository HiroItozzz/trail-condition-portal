from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Integer
from datetime import datetime, timezone, timedelta

class Base(DeclarativeBase):
    pass


JST = timezone(timedelta(hours=+9), 'JST')

class ConditionInfo(Base):
    __tablename__ = "condition_infos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    area_name: Mapped[str] = mapped_column(String, index=True)
    mountain_name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    hazard_type: Mapped[str] = mapped_column(Text)
    published_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_organization: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(JST), 
        onupdate=lambda: datetime.now(JST)
    )