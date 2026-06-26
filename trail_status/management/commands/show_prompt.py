import logging
import sys

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Max

from trail_status.models import DataSource
from trail_status.services import prompt_utils
from trail_status.services.prompt_utils import PromptFile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "情報源IDから現在のAI設定を確認"

    def add_arguments(self, parser):
        parser.add_argument("source_id", type=int, help="情報源ID")

    def handle(self, *args, **options):
        source_id = options.get("source_id")
        try:
            source = DataSource.objects.get(pk=source_id)
        except ObjectDoesNotExist:
            print(f"情報源ID {source_id} は存在しません", file=sys.stderr)
            print(f"情報源IDの最大値: {DataSource.objects.aggregate(Max('pk'))['pk__max']}")
            sys.exit(1)
        prompt_key = source.prompt_key
        filename = PromptFile.get_filename_from_data(source_id, prompt_key)
        config = PromptFile.load_merged_config(filename)

        print(config)
