import pytest
from trail_status.models import TrailCondition, DataSource, OrganizationType, StatusType, AreaName
from datetime import datetime, timedelta, date


@pytest.fixture(autouse=True)
def override_staticfiles(settings):
    settings.STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        }
    }


def create_sample_data_source(n: int | str = "", **kwargs) -> DataSource:
    defaults = dict(
        name=f"テスト機関{n}",
        organization_type=OrganizationType.MUNICIPALITY,
        prefecture_code=13,
        prompt_key=f"test_org_{n}",
        url1=f"https://sample{n}.com/",
        url2=f"https://sample{n}.com/data/",
        description=f"サンプル詳細説明{n}",
        data_format="WEB",
        area_name=AreaName.OKUTAMA,
        content_hash="",
        last_scraped_at=datetime.today() - timedelta(days=2),
        last_checked_at=datetime.today(),
    )
    defaults.update(kwargs)
    return DataSource.objects.create(**defaults)


def create_sample_condition(n: int | str = "", data_source=None, **kwargs) -> TrailCondition:
    data_source = data_source or create_sample_data_source(n)

    defaults = dict(
        source=data_source,
        url1=f"https://sample{n}.com/",
        trail_name=f"テスト道{n}",
        mountain_name_raw=f"テスト山{1}",
        title=f"テスト通行止め{1}",
        description=f"テスト詳細説明{1}",
        reported_at=date.today() - timedelta(days=2),
        resolved_at=None,
        status=StatusType.CLOSURE,
        area=AreaName.OKUTAMA,
        reference_url=f"https://sample{1}.com/ref",
        comment="テストコメント",
        mountain_group=None,
        ai_model="gemini-3-flash",
        prompt_file=f"{data_source.id:0>3}_{data_source.prompt_key}.yaml",
        ai_config={},
        disabled=False,
    )

    defaults.update(kwargs)
    return TrailCondition.objects.create(**defaults)


@pytest.fixture
def data_source():
    s = create_sample_data_source(1)
    yield s


@pytest.fixture
def sample_condition(data_source):
    t = create_sample_condition()
    yield t
