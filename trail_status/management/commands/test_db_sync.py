import json
from django.core.management.base import BaseCommand
from django.db import transaction

from trail_status.models.source import DataSource
from trail_status.services.schema import TrailConditionSchemaInternal
from trail_status.services.db_writer import sync_trail_conditions


class Command(BaseCommand):
    help = 'AI出力結果からDB同期をテスト'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-id',
            type=int,
            required=True,
            help='DataSourceのID'
        )
        parser.add_argument(
            '--json-file',
            type=str,
            help='AI出力JSONファイルのパス'
        )
        parser.add_argument(
            '--json-data',
            type=str,
            help='AI出力JSON文字列（直接入力）'
        )

    def handle(self, *args, **options):
        source_id = options['source_id']
        json_file = options.get('json_file')
        json_data = options.get('json_data')

        if not json_file and not json_data:
            self.stdout.write(
                self.style.ERROR('--json-file または --json-data のいずれかを指定してください')
            )
            return

        # DataSourceを取得
        try:
            source = DataSource.objects.get(id=source_id)
            self.stdout.write(f'データソース: {source.name}')
        except DataSource.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'DataSource ID {source_id} が見つかりません')
            )
            return

        # JSONデータを読み込み
        if json_file:
            with open(json_file, 'r', encoding='utf-8') as f:
                ai_output = json.load(f)
        else:
            ai_output = json.loads(json_data)

        # AI出力をInternal schemaに変換
        try:
            # ai_outputが既にtrail_condition_records形式か確認
            if 'trail_condition_records' in ai_output:
                ai_conditions = ai_output['trail_condition_records']
            elif 'conditions' in ai_output:
                ai_conditions = ai_output['conditions']
            else:
                self.stdout.write(
                    self.style.ERROR('JSONに"trail_condition_records"または"conditions"キーが見つかりません')
                )
                return

            internal_data_list = [
                TrailConditionSchemaInternal(
                    **condition,
                    url1=source.url1
                )
                for condition in ai_conditions
            ]

            self.stdout.write(f'変換完了: {len(internal_data_list)}件の条件')

            # DB同期実行
            with transaction.atomic():
                sync_trail_conditions(source, internal_data_list)

            self.stdout.write(
                self.style.SUCCESS(f'DB保存完了: {len(internal_data_list)}件')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'エラーが発生: {e}')
            )
            raise