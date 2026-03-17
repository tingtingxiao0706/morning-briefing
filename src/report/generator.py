from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from src.scrapers.base import BriefingSection

TEMPLATE_DIR = Path(__file__).parent
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class ReportGenerator:
    def __init__(self, output_dir: str = "./output", width: int = 800):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    def render_html(self, sections: List[BriefingSection], analysis=None) -> Path:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday = WEEKDAY_CN[now.weekday()]
        total_items = sum(len(s.items) for s in sections)

        template = self.env.get_template("template.html")
        html = template.render(
            date=date_str,
            weekday=weekday,
            sections=sections,
            total_items=total_items,
            analysis=analysis,
            generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            width=self.width,
        )

        html_path = self.output_dir / f"briefing_{date_str}.html"
        html_path.write_text(html, encoding="utf-8")
        logger.success(f"HTML report saved: {html_path}")
        return html_path

    async def screenshot(self, html_path: Path) -> Path:
        from playwright.async_api import async_playwright

        png_path = html_path.with_suffix(".png")
        file_url = html_path.resolve().as_uri()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": self.width, "height": 800})
            await page.goto(file_url, wait_until="networkidle")
            await page.wait_for_timeout(1500)
            full_height = await page.evaluate("document.body.scrollHeight")
            await page.set_viewport_size({"width": self.width, "height": full_height})
            await page.screenshot(path=str(png_path), full_page=True)
            await browser.close()

        logger.success(f"Screenshot saved: {png_path} ({os.path.getsize(png_path) / 1024:.0f} KB)")
        return png_path

    async def generate(self, sections: List[BriefingSection], analysis=None) -> tuple[Path, Path]:
        html_path = self.render_html(sections, analysis=analysis)
        png_path = await self.screenshot(html_path)
        return html_path, png_path
