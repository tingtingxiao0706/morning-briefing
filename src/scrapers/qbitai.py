from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper, BriefingItem

QBITAI_URL = "https://www.qbitai.com/"


class QbitAIScraper(BaseScraper):
    """量子位 — 追踪人工智能新趋势"""

    name = "量子位"
    icon = "⚛️"
    color = "#7C4DFF"

    async def fetch(self) -> List[BriefingItem]:
        async with self._client() as client:
            resp = await client.get(QBITAI_URL)
            resp.raise_for_status()
            return self._parse(resp.text)

    def _parse(self, html: str) -> List[BriefingItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[BriefingItem] = []
        seen: set[str] = set()

        # 量子位文章链接格式: /2026/03/388387.html
        for a in soup.select('a[href*="/20"]'):
            href = a.get("href", "")
            title = a.get_text(strip=True)

            if not title or len(title) < 8 or title in seen:
                continue
            if not href or ".html" not in href:
                continue

            seen.add(title)
            url = href if href.startswith("http") else f"https://www.qbitai.com{href}"

            items.append(
                BriefingItem(title=title, url=url, summary="", source=self.name)
            )
            if len(items) >= self.count:
                break

        return items
