import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
class TestTrailCondition:
    pytestmark = pytest.mark.django_db

    def test_condition_creation(self): ...
