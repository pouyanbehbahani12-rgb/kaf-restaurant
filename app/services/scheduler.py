"""APScheduler weekly content generation job."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def run_scheduled_generation():
    """Run the weekly content generation (called by scheduler)."""
    logger.info("Scheduled weekly generation starting...")
    try:
        from app.database import SessionLocal
        from app.services.content_generator import run_weekly_generation

        db = SessionLocal()
        try:
            # Consume the generator
            for msg in run_weekly_generation(db):
                logger.info("Generation: %s", msg.strip())
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduled generation failed: %s", exc)


def start_scheduler():
    parts = settings.weekly_generation_cron.split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )
    else:
        # Default: every Monday at 9am
        trigger = CronTrigger(day_of_week="mon", hour=9, minute=0)

    scheduler.add_job(
        run_scheduled_generation,
        trigger=trigger,
        id="weekly_generation",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with cron: %s", settings.weekly_generation_cron)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
