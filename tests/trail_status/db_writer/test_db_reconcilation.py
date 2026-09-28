from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from trail_status.models import AreaName, StatusType, TrailCondition
from trail_status.services.db_writer import DbWriter
from trail_status.services.prompt_utils import PromptFile
from trail_status.services.types import ConditionSchemaAiInternal, LlmModel, ResultSingle, SourceSchemaSingle


@pytest.fixture
def mock_DbWriter(llm_config_factory):
    """DBライターのモック"""

    llm_config = llm_config_factory(LlmModel.DEEPSEEK_CHAT)

    sample_source_schema = SourceSchemaSingle(
        id=100, name="sample", url1="http://url1.com", prompt_file=PromptFile(prompt="test"), content_hash=None
    )
    sample_result_single = ResultSingle(success=True, message="OK", config=llm_config)
    return DbWriter(sample_source_schema, sample_result_single)


@pytest.fixture
def mock_existing_record():
    """DBの登山道状況レコードのモック"""
    sample_existing_record = MagicMock(
        spec=TrailCondition,
        id=100,
        disabled=False,
        mountain_name_raw="テスト山",
        trail_name="テスト道",
        title="通行止め",
        description="テスト詳細",
        status=StatusType.CLEAR,
        resolved_at=date.today(),
        created_at=datetime.now(tz=timezone.utc) - timedelta(days=2),
    )
    return sample_existing_record


@pytest.fixture
def mock_ai_result_update():
    """更新ありモック"""
    sample_ai_result = ConditionSchemaAiInternal(
        mountain_name_raw="テスト山",
        trail_name="テスト道",
        title="通行止め",
        description="詳細：通行止め解除",
        reported_at=date.today(),
        status=StatusType.CLOSURE,  # ステータスタイプ変更で更新検知
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )
    return sample_ai_result


@pytest.fixture
def mock_ai_result_create():
    """新規登録モック"""
    sample_ai_result = ConditionSchemaAiInternal(
        mountain_name_raw="サンプル山",
        trail_name="サンプル道",
        title="通行止め",
        description="サンプル",
        reported_at=date.today(),
        status=StatusType.CLEAR,
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )
    return sample_ai_result


@pytest.fixture
def mock_ai_result_no_change():
    """更新なしモック"""
    sample_ai_result = ConditionSchemaAiInternal(
        mountain_name_raw="テスト山",
        trail_name="テスト道",
        title="通行止め",
        description="詳細",
        reported_at=date.today(),
        status=StatusType.CLEAR,
        resolved_at=date.today(),
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )
    return sample_ai_result


### _reconcile_records
def test_reconcile_records_update(mock_existing_record, mock_ai_result_update, mock_DbWriter):
    """データ照合ロジック AI変更検知+1件更新のテスト"""
    to_update, to_create = mock_DbWriter._reconcile_records([mock_existing_record], [mock_ai_result_update])

    # Statusが変更されているため更新1件
    assert len(to_update) == 1
    assert len(to_create) == 0


def test_reconcile_records_create(mock_existing_record, mock_ai_result_create, mock_DbWriter):
    """データ照合ロジック 新規登録のテスト"""
    to_update, to_create = mock_DbWriter._reconcile_records([mock_existing_record], [mock_ai_result_create])

    # 全く異なる出力のため新規登録1件
    assert len(to_update) == 0
    assert len(to_create) == 1


def test_reconcile_records_no_change(mock_existing_record, mock_ai_result_no_change, mock_DbWriter):
    """データ照合ロジック AI変更検知+更新なしのテスト"""
    to_update, to_create = mock_DbWriter._reconcile_records([mock_existing_record], [mock_ai_result_no_change])

    # 既存と全く同じAI出力のため更新0件+新規0件
    assert len(to_update) == 0
    assert len(to_create) == 0


def test_reconcile_records_new_source(mock_ai_result_no_change, mock_DbWriter):
    """データ照合ロジック 新規情報源のためdisabled=True"""
    to_update, to_create = mock_DbWriter._reconcile_records([], [mock_ai_result_no_change])

    # 新規情報源は人間が確認するのでdisabled=True
    assert len(to_update) == 0
    assert len(to_create) == 1
    assert to_create[0].disabled


### _calculate_simitarity
def test_calculate_similarity_same_data(mock_existing_record, mock_ai_result_no_change, mock_DbWriter):
    """類似度照合ロジック 同一データ"""
    similarity = mock_DbWriter._calculate_similarity(mock_existing_record, mock_ai_result_no_change)
    assert similarity == 1


def test_calculate_similarity_different_data(mock_existing_record, mock_ai_result_create, mock_DbWriter):
    """類似度照合ロジック 異なるデータ"""
    similarity = mock_DbWriter._calculate_similarity(mock_existing_record, mock_ai_result_create)
    print("類似度（different data）:", similarity)
    assert similarity <= 0.6


def test_calculate_similarity_similar_data(mock_existing_record, mock_ai_result_update, mock_DbWriter):
    """類似度照合ロジック 類似データ"""
    similarity = mock_DbWriter._calculate_similarity(mock_existing_record, mock_ai_result_update)
    print("類似度（similar data）:", similarity)
    assert similarity >= 0.7


### _reconcile_records 複数件の割り当て（docs/260927-test-plan.md「2. レコード照合の複数件のケース」A）


def make_existing_record(id_: int, *, status: StatusType, resolved_at: date | None = None, disabled: bool = False):
    """テスト用の既存レコードのモックを作る

    類似度は monkeypatch で差し替えるため、割り当ての判定に使う属性のみ指定する。
    """
    return MagicMock(spec=TrailCondition, id=id_, disabled=disabled, status=status, resolved_at=resolved_at)


def make_ai_record(title: str, *, status: StatusType, resolved_at: date | None = None) -> ConditionSchemaAiInternal:
    """テスト用のAI出力を作る（titleでどの出力かを見分ける）"""
    return ConditionSchemaAiInternal(
        trail_name="道",
        title=title,
        status=status,
        resolved_at=resolved_at,
        area=AreaName.OKUTAMA,
        url1="http://url1.com/",
        ai_config={},
    )


def patch_similarity(monkeypatch: pytest.MonkeyPatch, table: dict[tuple[int, str], float]) -> None:
    """(既存レコードのid, AI出力のtitle) をキーにした類似度で _calculate_similarity を差し替える

    dictにない組み合わせは0.0を返す。
    """

    def fake_similarity(self, existing, ai_record):
        return table.get((existing.id, ai_record.title), 0.0)

    monkeypatch.setattr(DbWriter, "_calculate_similarity", fake_similarity)


class TestReconcileRecordsAssignment:
    """_reconcile_records の割り当てのしくみのテスト（既存レコード・AI出力とも複数件）"""

    def test_a1_higher_score_wins_competition(self, monkeypatch, mock_DbWriter):
        """A-1: 取り合いになったら渡した順ではなくスコアの高い方が勝ち、負けた方は新規作成になる"""
        x = make_existing_record(101, status=StatusType.CLEAR)
        a = make_ai_record("a", status=StatusType.CLOSURE)
        b = make_ai_record("b", status=StatusType.CLOSURE)
        patch_similarity(monkeypatch, {(101, "a"): 0.95, (101, "b"): 0.80})

        to_update, to_create = mock_DbWriter._reconcile_records([x], [a, b])

        assert [r.title for r in to_update] == ["a"]
        assert [r.title for r in to_create] == ["b"]

    def test_a2_result_is_same_when_order_is_reversed(self, monkeypatch, mock_DbWriter):
        """A-2: A-1のAI出力を逆順で渡しても結果は変わらない（渡す順ではなくスコアで決まる）"""
        x = make_existing_record(101, status=StatusType.CLEAR)
        a = make_ai_record("a", status=StatusType.CLOSURE)
        b = make_ai_record("b", status=StatusType.CLOSURE)
        patch_similarity(monkeypatch, {(101, "a"): 0.95, (101, "b"): 0.80})

        to_update, to_create = mock_DbWriter._reconcile_records([x], [b, a])

        assert [r.title for r in to_update] == ["a"]
        assert [r.title for r in to_create] == ["b"]

    def test_a3_second_place_still_matches_remaining_record(self, monkeypatch, mock_DbWriter):
        """A-3: 一番手が既存レコードを取ったあと、残った既存レコードに二番手が結びつき新規作成は出ない"""
        x = make_existing_record(101, status=StatusType.CLEAR)
        y = make_existing_record(102, status=StatusType.CLEAR)
        a = make_ai_record("a", status=StatusType.CLOSURE)
        b = make_ai_record("b", status=StatusType.CLOSURE)
        patch_similarity(
            monkeypatch,
            {(101, "a"): 0.90, (102, "a"): 0.85, (101, "b"): 0.80, (102, "b"): 0.75},
        )

        to_update, to_create = mock_DbWriter._reconcile_records([x, y], [a, b])

        assert {r.id: r.title for r in to_update} == {101: "a", 102: "b"}
        assert to_create == []

    def test_a4_threshold_boundary_is_inclusive(self, monkeypatch, mock_DbWriter):
        """A-4: しきい値ちょうどは結びつき、しきい値未満は結びつかず新規作成になる"""
        x = make_existing_record(101, status=StatusType.CLEAR)
        y = make_existing_record(102, status=StatusType.CLEAR)
        a = make_ai_record("a", status=StatusType.CLOSURE)
        b = make_ai_record("b", status=StatusType.CLOSURE)
        patch_similarity(
            monkeypatch,
            {
                (101, "a"): DbWriter.SIMILARITY_THRESHOLD,
                (102, "b"): DbWriter.SIMILARITY_THRESHOLD - 0.01,
            },
        )

        to_update, to_create = mock_DbWriter._reconcile_records([x, y], [a, b])

        assert [r.title for r in to_update] == ["a"]
        assert [r.title for r in to_create] == ["b"]

    def test_a5_disabled_record_is_excluded_from_candidates(self, monkeypatch, mock_DbWriter):
        """A-5: disabledな既存レコードは候補から外れ、AI出力は新規作成になる（disabled=Falseで）"""
        x = make_existing_record(101, status=StatusType.CLEAR, disabled=True)
        a = make_ai_record("a", status=StatusType.CLOSURE)
        patch_similarity(monkeypatch, {(101, "a"): 1.0})

        to_update, to_create = mock_DbWriter._reconcile_records([x], [a])

        assert to_update == []
        assert [r.title for r in to_create] == ["a"]
        assert to_create[0].disabled is False

    def test_a6_unchanged_pair_is_neither_updated_nor_created(self, monkeypatch, mock_DbWriter):
        """A-6: 結びついても内容に変更がなければ更新せず、新規作成もしない"""
        same_date = date.today()
        x = make_existing_record(101, status=StatusType.CLEAR, resolved_at=same_date)
        y = make_existing_record(102, status=StatusType.CLEAR)
        a = make_ai_record("a", status=StatusType.CLEAR, resolved_at=same_date)
        b = make_ai_record("b", status=StatusType.CLOSURE)
        patch_similarity(monkeypatch, {(101, "a"): 0.9, (102, "b"): 0.9})

        to_update, to_create = mock_DbWriter._reconcile_records([x, y], [a, b])

        assert [r.title for r in to_update] == ["b"]
        assert to_create == []

    def test_a7_unmatched_existing_record_is_left_untouched(self, monkeypatch, mock_DbWriter):
        """A-7: 結びつかなかった既存レコードはto_updateに含まれず、内容も変わらない"""
        x = make_existing_record(101, status=StatusType.CLEAR)
        y = make_existing_record(102, status=StatusType.CLEAR)
        a = make_ai_record("a", status=StatusType.CLOSURE)
        patch_similarity(monkeypatch, {(101, "a"): 0.9})

        to_update, to_create = mock_DbWriter._reconcile_records([x, y], [a])

        assert [r.title for r in to_update] == ["a"]
        assert y not in to_update
        assert to_create == []
        assert y.disabled is False
        assert y.status == StatusType.CLEAR
        assert y.resolved_at is None
