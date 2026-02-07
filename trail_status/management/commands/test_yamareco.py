import time

import requests
from django.core.management.base import BaseCommand

from trail_status.models.condition import TrailCondition
from trail_status.models.mountain import AreaName


class Command(BaseCommand):
    help = "ヤマレコAPIのテスト"

    def add_arguments(self, parser):
        parser.add_argument("--source", type=int, help="処理対象の情報源id")

    def handle(self, *args, **options):
        source_id = options.get("source")

        if source_id:
            trails = TrailCondition.objects.filter(source__id=source_id)
        else:
            trails = TrailCondition.objects.all()

        for trail in trails:
            area_id = AreaName.get_yamareco_area_id(trail.area)
            name = trail.mountain_name_raw
            result = self.get_resource(name=name, area_id=area_id)
            self.print_summary(trail, area_id, result)
            if not len(result):
                area_id=300
                print(f"試行2回目 (area_id={area_id})")
                result = self.get_resource(name=name, area_id=area_id)
                self.print_summary(trail, area_id, result)


    def get_resource(self, **kwargs) -> list:
        name = kwargs.get("name")
        area_id = kwargs.get("area_id")
        type_id = kwargs.get("type_id", 0)

        url = "https://api.yamareco.com/api/v1/searchPoi"
        data = {"name": name, "area_id": area_id, "page": 1, "type_id": type_id}

        res = requests.post(url, data=data)
        result = res.json()
        time.sleep(0.1)  # APIレート制限対策
        if result.get("err") == 0 and "poilist" in result:
            return result["poilist"]
        return []

    def print_summary(self, trail, area_id, result):
        name = trail.mountain_name_raw

        if result:
            print(f"✓ {name} (area_id={area_id}): {len(result)}件")
            for poi in result[:3]:
                print(f"    - {poi['name']} ({poi.get('elevation', '?')}m) area: {poi["area"]} [{poi.get('lat')}, {poi.get('lon')}]")
                #print(" | ".join([f"{key}: {value}" for key, value in poi.items()]))

        else:
            print(f"✗ {name} (area_id={area_id}): 見つからず")
