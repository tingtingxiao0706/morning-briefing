"""Morning Briefing Agent — entry point.

Usage:
    python main.py              # Run once immediately
    python main.py --schedule   # Start scheduled mode (default: daily at 08:00)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)
logger.add(
    "output/briefing.log",
    rotation="7 days",
    retention="30 days",
    level="DEBUG",
)


def main():
    parser = argparse.ArgumentParser(description="Morning Briefing Agent")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in scheduled mode (default cron from config.yaml)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    args = parser.parse_args()

    if args.schedule:
        import yaml

        with open(args.config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        cron = config.get("schedule", {}).get("cron", "0 8 * * *")

        from src.scheduler import start_scheduler

        start_scheduler(cron)
    else:
        from src.agent import MorningBriefingAgent

        agent = MorningBriefingAgent(config_path=args.config)
        result = asyncio.run(agent.run())
        logger.info(f"Report saved to: {result}")


if __name__ == "__main__":
    main()
