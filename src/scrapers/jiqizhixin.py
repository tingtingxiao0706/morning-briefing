from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper, BriefingItem

JIQIZHIXIN_URL = "https://www.jiqizhixin.com/"


class JiqizhixinScraper(BaseScraper):
    """机器之心 — 国内领先的 AI 资讯媒体"""

    name = "机器之心"
    icon = "🤖"
    color = "#1E88E5"

    async def fetch(self) -> List[BriefingItem]:
        async with self._client() as client:
            resp = await client.get(JIQIZHIXIN_URL)
            resp.raise_for_status()
            return self._parse(resp.text)

    def _parse(self, html: str) -> List[BriefingItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[BriefingItem] = []
        seen: set[str] = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            title = a.get_text(strip=True)

            if not title or len(title) < 8 or title in seen:
                continue

            is_article = (
                "pro.jiqizhixin.com/reference/" in href
                or "/articles/" in href
                or "/dailies/" in href
            )
            if not is_article:
                continue

            seen.add(title)
            url = href if href.startswith("http") else f"https://www.jiqizhixin.com{href}"

            items.append(
                BriefingItem(title=title, url=url, summary="", source=self.name)
            )
            if len(items) >= self.count:
                break

        return items
