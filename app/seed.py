from datetime import datetime
from app.database import SessionLocal
from app.models.danger import DangerInfo

def seed_data():
    db = SessionLocal()
    
    dangers = [
        DangerInfo(
            area_name="北アルプス",
            source="yamap",
            mountain_name="槍ヶ岳",
            danger_type="落石",
            description="槍沢ルートで落石多発",
            reported_date=datetime(2025, 12, 10),
            original_url="https://yamap.com/activities/12345",
            created_at=datetime.now()
        ),
        DangerInfo(
            area_name="北アルプス",
            source="yamareco",
            mountain_name="槍ヶ岳",
            danger_type="崩落",
            description="北鎌尾根で崩落跡が見られた",
            reported_date=datetime(2025, 12, 9),
            original_url="https://yamareco.com/modules/yamareco/detail.php?id=67890",
            created_at=datetime.now()
        )
    ]
    
    db.add_all(dangers)
    db.commit()
    
    print("テストデータを挿入しました")
    db.close()

if __name__ == "__main__":
    seed_data()