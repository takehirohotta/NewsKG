"""
APScheduler定期実行モジュール

毎日6:00にニュースパイプラインを自動実行します。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


async def run_daily_pipeline():
    """
    日次パイプラインを実行
    
    1. RSS取得
    2. RDF変換
    3. Fusekiアップロード
    """
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        logger.info("=" * 60)
        logger.info(f"Daily pipeline started at {datetime.now()}")
        logger.info("=" * 60)
        
        from fetch_rss import main as fetch_rss
        logger.info("Step 1/3: Fetching RSS feeds...")
        fetch_result = fetch_rss()
        logger.info(f"RSS fetch completed: {fetch_result.get('total_articles', 0)} articles")
        
        from run_pipeline import main as run_pipeline
        logger.info("Step 2/3: Running RDF pipeline...")
        pipeline_result = run_pipeline(upload=True)
        logger.info(f"Pipeline completed: {pipeline_result}")
        
        logger.info("Step 3/3: Pipeline completed successfully")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "articles_fetched": fetch_result.get('total_articles', 0),
            "pipeline_result": pipeline_result,
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


def job_listener(event):
    """ジョブ実行イベントのリスナー"""
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} completed successfully")


def init_scheduler() -> AsyncIOScheduler:
    """スケジューラーを初期化"""
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    scheduler = AsyncIOScheduler(
        timezone="Asia/Tokyo",
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        }
    )
    
    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=6, minute=0),
        id="daily_pipeline",
        name="Daily News Pipeline",
        replace_existing=True,
    )
    
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    logger.info("Scheduler initialized with daily pipeline job at 06:00 JST")
    
    return scheduler


def start_scheduler():
    """スケジューラーを開始"""
    global scheduler
    
    if scheduler is None:
        scheduler = init_scheduler()
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    """スケジューラーを停止"""
    global scheduler
    
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduler_status():
    """スケジューラーのステータスを取得"""
    global scheduler
    
    if scheduler is None:
        return {"running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
