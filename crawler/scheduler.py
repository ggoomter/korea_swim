from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from crawler.main import crawl_and_save
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_scheduler():
    """
    주기적 데이터 업데이트 스케줄러
    """
    scheduler = BackgroundScheduler()

    # 매주 일요일 새벽 3시에 전체 크롤링
    scheduler.add_job(
        crawl_and_save,
        CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='weekly_crawl',
        name='주간 수영장 데이터 업데이트',
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ 스케줄러 시작됨 - 매주 일요일 03:00 크롤링")

    return scheduler

if __name__ == "__main__":
    scheduler = start_scheduler()

    try:
        # 스케줄러 유지
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("스케줄러 종료")
