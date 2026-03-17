from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base import BaseScraper, BriefingItem

AITOP100_URL = "https://www.aitop100.cn/"


class AiTop100Scraper(BaseScraper):
    """AITOP100 — AI 工具导航与排行

    Vue SSR 应用，通过 window.__INITIAL_STATE__ 获取数据。
    """

    name = "AITOP100"
    icon = "🏆"
    color = "#FF6F00"

    async def fetch(self) -> List[BriefingItem]:
        async with self._client() as client:
            resp = await client.get(AITOP100_URL)
            resp.raise_for_status()

            # 优先从 __INITIAL_STATE__ JSON 提取
            items = self._parse_initial_state(resp.text)
            if items:
                return items[: self.count]

            # 备用：从 HTML 元素提取
            items = self._parse_html(resp.text)
            if items:
                return items[: self.count]

            return self._static_fallback()

    def _parse_initial_state(self, html: str) -> List[BriefingItem]:
        m = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*(?:</script>|;)",
            html,
            re.DOTALL,
        )
        if not m:
            return []

        try:
            state = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            return []

        items: List[BriefingItem] = []
        seen: set[str] = set()

        # 从 homeStore.activities 获取最新 AI 资讯
        activities = (
            state.get("homeStore", {}).get("activities")
            or state.get("homeStore", {}).get("articleList")
            or []
        )
        for act in activities:
            name = act.get("name", "") or act.get("title", "")
            if not name or name in seen:
                continue
            seen.add(name)
            url_path = act.get("urlPath", "") or act.get("originalLink", "")
            url = url_path if url_path.startswith("http") else f"{AITOP100_URL}{url_path.lstrip('/')}" if url_path else AITOP100_URL
            source_tag = act.get("source", "")
            summary = source_tag if source_tag else ""

            items.append(
                BriefingItem(title=name, url=url, summary=summary, source=self.name)
            )

        # 从 toolsStore 获取推荐工具
        if len(items) < self.count:
            tools = (
                state.get("toolsStore", {}).get("toolsRecommendedList")
                or state.get("toolsStore", {}).get("homelists")
                or state.get("toolsStore", {}).get("homenewlist")
                or []
            )
            for tool in tools:
                name = tool.get("name", "") or tool.get("title", "") or tool.get("toolName", "")
                if not name or name in seen:
                    continue
                seen.add(name)
                desc = tool.get("description", "") or tool.get("desc", "") or ""
                if desc:
                    clean = BeautifulSoup(desc, "lxml").get_text(strip=True)[:80]
                else:
                    clean = ""
                url_path = tool.get("urlPath", "") or tool.get("url", "")
                url = url_path if url_path.startswith("http") else f"{AITOP100_URL}{url_path.lstrip('/')}" if url_path else AITOP100_URL

                items.append(
                    BriefingItem(title=name, url=url, summary=clean, source=self.name)
                )

        return items

    def _parse_html(self, html: str) -> List[BriefingItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[BriefingItem] = []
        seen: set[str] = set()

        for card in soup.select(".component-infocard, .el-card"):
            link = card.select_one("a[href]")
            if not link:
                continue
            href = link.get("href", "")
            text = card.get_text(strip=True)[:60]
            if not text or len(text) < 3 or text in seen:
                continue
            seen.add(text)
            url = href if href.startswith("http") else f"{AITOP100_URL}{href.lstrip('/')}"
            items.append(
                BriefingItem(title=text, url=url, summary="", source=self.name)
            )
            if len(items) >= self.count:
                break
        return items

    @staticmethod
    def _static_fallback() -> List[BriefingItem]:
        return [
            BriefingItem(
                title="访问 AITOP100 发现热门 AI 工具",
                url=AITOP100_URL,
                summary="aitop100.cn — AI 工具导航与排行榜",
                source="AITOP100",
            )
        ]
