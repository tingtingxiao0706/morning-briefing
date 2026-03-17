from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Any

import yaml
from dotenv import load_dotenv
from loguru import logger

from src.scrapers import ALL_SCRAPERS, BaseScraper, BriefingSection
from src.analyzer import AIAnalyzer, AnalysisResult
from src.report.generator import ReportGenerator
from src.notifier.feishu import FeishuNotifier


class MorningBriefingAgent:
    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self.config = self._load_config(config_path)
        self.scrapers = self._init_scrapers()
        self.analyzer = self._init_analyzer()
        self.report_gen = ReportGenerator(
            output_dir=self.config.get("report", {}).get("output_dir", "./output"),
            width=self.config.get("report", {}).get("width", 800),
        )
        self.notifier = self._init_notifier()

    @staticmethod
    def _load_config(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_scrapers(self) -> list[BaseScraper]:
        scrapers = []
        for site in self.config.get("sites", []):
            name = site.get("name")
            if not site.get("enabled", True):
                continue
            cls = ALL_SCRAPERS.get(name)
            if cls is None:
                logger.warning(f"Unknown scraper: {name}")
                continue
            scrapers.append(cls(count=site.get("count", 5)))
        return scrapers

    def _init_analyzer(self) -> AIAnalyzer | None:
        cfg = self.config.get("llm", {})
        if not cfg.get("enabled", True):
            return None

        api_key = os.getenv("LLM_API_KEY", cfg.get("api_key", ""))
        if not api_key or api_key.startswith("$"):
            logger.warning("LLM API key not configured — AI analysis disabled")
            return None

        base_url = os.getenv("LLM_BASE_URL", cfg.get("base_url", "https://api.deepseek.com/v1"))
        model = os.getenv("LLM_MODEL", cfg.get("model", "deepseek-chat"))

        logger.info(f"AI analyzer: model={model}, base={base_url}")
        return AIAnalyzer(api_key=api_key, base_url=base_url, model=model)

    def _init_notifier(self) -> FeishuNotifier | None:
        cfg = self.config.get("feishu", {})
        app_id = os.getenv("FEISHU_APP_ID", cfg.get("app_id", ""))
        app_secret = os.getenv("FEISHU_APP_SECRET", cfg.get("app_secret", ""))
        chat_id = os.getenv("FEISHU_CHAT_ID", cfg.get("chat_id", ""))

        if not app_id or app_id.startswith("$") or not app_secret or app_secret.startswith("$"):
            logger.warning("Feishu credentials not configured — notification disabled")
            return None
        if not chat_id or chat_id.startswith("$"):
            logger.warning("Feishu chat_id not configured — notification disabled")
            return None

        return FeishuNotifier(app_id=app_id, app_secret=app_secret, chat_id=chat_id)

    @staticmethod
    def _build_report_url(html_path: Path) -> str | None:
        base = os.getenv("REPORT_BASE_URL", "")
        if not base:
            return None
        return f"{base.rstrip('/')}/{html_path.name}"

    async def run(self) -> Path:
        logger.info("=== Morning Briefing Agent START ===")
        t0 = time.time()

        # 1. Scrape all sources in parallel
        logger.info(f"Step 1/4: Scraping {len(self.scrapers)} sources...")
        tasks = [s.scrape() for s in self.scrapers]
        sections: list[BriefingSection] = await asyncio.gather(*tasks)
        total_items = sum(len(s.items) for s in sections)
        logger.info(f"Scraping done: {total_items} items from {len(sections)} sources")

        # 2. AI analysis
        analysis: AnalysisResult | None = None
        if self.analyzer:
            logger.info("Step 2/4: Running AI analysis...")
            analysis = await self.analyzer.analyze(sections)
        else:
            logger.info("Step 2/4: AI analysis not configured, skipping")

        # 3. Generate report
        logger.info("Step 3/4: Generating HTML report & screenshot...")
        html_path, png_path = await self.report_gen.generate(sections, analysis=analysis)

        # 4. Send to Feishu
        if self.notifier:
            logger.info("Step 4/4: Sending to Feishu...")
            report_url = self._build_report_url(html_path)
            try:
                ok = await self.notifier.send(sections, png_path, report_url=report_url)
                if ok:
                    logger.success("Feishu notification sent!")
                else:
                    logger.error("Feishu notification failed")
            except Exception as e:
                logger.error(f"Feishu notification error: {e}")
        else:
            logger.info("Step 4/4: Feishu not configured, skipping notification")

        elapsed = time.time() - t0
        logger.info(f"=== Morning Briefing Agent DONE in {elapsed:.1f}s ===")
        return png_path
