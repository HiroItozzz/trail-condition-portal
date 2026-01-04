import logging
import unicodedata

from trail_status.models.condition import TrailCondition
from trail_status.models.source import DataSource

from .llm_client import LlmConfig
from .schema import TrailConditionSchemaInternal

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """全角半角・空白を揃えて比較の精度を上げる"""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip().replace(" ", "").replace("　", "")


def sync_trail_conditions(
    source: DataSource, ai_data_list: list[TrailConditionSchemaInternal], config: LlmConfig, prompt_filename: str
) -> None:
    """
    AIの抽出データ(Pydantic)をDjango DBへ同期する。
    既存レコードとの同定。レコードがあれば更新、なければ作成を行う。

    Args:
        source: データソース
        ai_data_list: AI抽出データリスト
        config: LlmConfig（AI設定情報）
        prompt_file: 使用したプロンプトファイル名
    """
    for data in ai_data_list:
        # 1. AIの出力を正規化（空白や全角半角の揺れを取る）
        # これにより、AIが「雲取山 」と出しても「雲取山」として扱う
        normalized_m_name = normalize_text(data.mountain_name_raw)
        normalized_t_name = normalize_text(data.trail_name)

        # 2. 既存レコードの検索
        # ※ DB側も同様の正規化で比較したいところですが、
        #    まずは「保存されている値」を正規化したものと比較します。
        existing_record = None
        all_potential_records = TrailCondition.objects.filter(source=source, disabled=False)
        for record in all_potential_records:
            # 山名と登山道・区間名でまず同定
            if (
                normalize_text(record.mountain_name_raw) == normalized_m_name
                and normalize_text(record.trail_name) == normalized_t_name
            ):
                existing_record = record
                break

        if existing_record:
            # 2. 内容の比較（タイトル、説明、ステータスに変更があるか）
            # reported_at が今日の日付に更新されているかもチェック対象に含める
            has_changed = (
                existing_record.title != data.title
                or existing_record.description != data.description
                or existing_record.status != data.status
                or existing_record.reported_at != data.reported_at
                or existing_record.resolved_at != data.resolved_at
            )

            if has_changed:
                existing_record.title = data.title
                existing_record.description = data.description
                existing_record.status = data.status
                existing_record.reported_at = data.reported_at
                existing_record.resolved_at = data.resolved_at
                # AI関連情報を更新
                existing_record.ai_model = config.model
                existing_record.prompt_file = prompt_filename
                ai_config = {
                    k: v
                    for k, v in {
                        "temperature": config.temperature,
                        "thinking_budget": config.thinking_budget,
                    }.items()
                    if v is not None
                }
                existing_record.ai_config = ai_config
                # save() により auto_now=True の updated_at が更新される
                existing_record.save()
                logger.info(f"レコード更新: {normalized_m_name}/{normalized_t_name} (ID: {existing_record.id})")
        else:
            # 3. 新規レコードの作成
            # mountain_group は signals.py が MountainAlias に基づいて自動解決する
            generated_data = data.model_dump(exclude={"mountain_name_raw", "trail_name"})
            ai_config = {
                k: v
                for k, v in {
                    "temperature": config.temperature,
                    "thinking_budget": config.thinking_budget,
                }.items()
                if v is not None
            }

            new_record = TrailCondition.objects.create(
                source=source,
                mountain_name_raw=data.mountain_name_raw,
                trail_name=data.trail_name,
                ai_model=config.model,
                prompt_file=prompt_filename,
                ai_config=ai_config,
                **generated_data,
            )
            logger.info(f"新規レコード作成: {normalized_m_name}/{normalized_t_name} (ID: {new_record.id})")
