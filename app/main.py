from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.danger import Base, DangerInfo

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "Trail Condition Search API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/search")
async def search_dangers(mountain: str = None, keyword: str = None, db: Session = Depends(get_db)):
    query = db.query(DangerInfo)

    if mountain:
        query = query.filter(DangerInfo.mountain_name.contains(mountain))

    if keyword:
        query = query.filter(DangerInfo.description.contains(keyword))

    results = query.all()

    return {
        "count": len(results),
        "results": [
            {
                "area": r.area_name,
                "source": r.source,
                "mountain": r.mountain_name,
                "danger_type": r.danger_type,
                "description": r.description,
                "date": r.reported_date.isoformat() if r.reported_date else None,
                "url": r.original_url,
            }
            for r in results
        ],
    }
