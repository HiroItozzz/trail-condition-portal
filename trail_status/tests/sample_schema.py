import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from pprint import pprint

from pydantic import BaseModel, Field

from trail_status.models.condition import StatusType


class TrailConditionSchema(BaseModel):
    url1: str = Field(default="http://sample.com")  # プロンプトには含めない
    status: StatusType = Field(description="状況種別")


schema = TrailConditionSchema.model_json_schema(mode="validation")
pprint(schema)
