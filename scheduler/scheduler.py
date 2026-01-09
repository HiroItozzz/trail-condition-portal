import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from .jobs import sync_trail_conditions_job

logger = logging.getLogger(__name__)

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # 毎日深夜 02:00 に実行する設定
    scheduler.add_job(
        sync_trail_conditions_job,
        trigger=CronTrigger(hour="02", minute="00"),
        id="sync_trail_conditions",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APSchedulerを開始しました (毎日 02:00 実行)")
