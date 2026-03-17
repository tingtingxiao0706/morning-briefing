from __future__ import annotations

import asyncio

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


def _run_agent():
    from src.agent import MorningBriefingAgent

    agent = MorningBriefingAgent()
    asyncio.run(agent.run())


def start_scheduler(cron_expr: str = "0 8 * * *"):
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
    )

    scheduler = BlockingScheduler()
    scheduler.add_job(_run_agent, trigger, id="morning_briefing", name="Morning Briefing")

    logger.info(f"Scheduler started with cron: {cron_expr}")
    logger.info("Press Ctrl+C to exit")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
