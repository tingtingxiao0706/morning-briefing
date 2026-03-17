from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List

import httpx
from loguru import logger


@dataclass
class BriefingItem:
    title: str
    url: str
    summary: str = ""
    score: int | None = None
    source: str = ""


@dataclass
class BriefingSection:
    source: str
    icon: str
    color: str
    items: List[BriefingItem] = field(default_factory=list)


class BaseScraper(abc.ABC):
    name: str = "base"
    icon: str = "📰"
    color: str = "#333333"

    def __init__(self, count: int = 5):
        self.count = count

    async def scrape(self) -> BriefingSection:
        logger.info(f"[{self.name}] Fetching top {self.count} items...")
        try:
            items = await self.fetch()
            logger.success(f"[{self.name}] Got {len(items)} items")
            return BriefingSection(
                source=self.name,
                icon=self.icon,
                color=self.color,
                items=items,
            )
        except Exception as e:
            logger.error(f"[{self.name}] Scrape failed: {e}")
            return BriefingSection(
                source=self.name,
                icon=self.icon,
                color=self.color,
                items=[
                    BriefingItem(
                        title=f"[{self.name}] 抓取失败",
                        url="",
                        summary=str(e),
                        source=self.name,
                    )
                ],
            )

    @abc.abstractmethod
    async def fetch(self) -> List[BriefingItem]:
        ...

    @staticmethod
    def _client(**kwargs) -> httpx.AsyncClient:
        defaults = dict(
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )
            },
        )
        defaults.update(kwargs)
        return httpx.AsyncClient(**defaults)
