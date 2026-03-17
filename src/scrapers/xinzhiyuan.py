from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper, BriefingItem

SOGOU_WX_SEARCH = "https://weixin.sogou.com/weixin"


class XinzhiyuanScraper(BaseScraper):
    """新智元 — AI 产业新媒体（微信公众号）

    新智元主要通过微信公众号发布内容，无独立网站。
    使用搜狗微信搜索获取最新文章。
    """

    name = "新智元"
    icon = "🧠"
    color = "#E53935"

    async def fetch(self) -> List[BriefingItem]:
        async with self._client() as client:
            # 搜狗微信搜索：搜索公众号文章
            resp = await client.get(
                SOGOU_WX_SEARCH,
                params={"type": "2", "query": "新智元", "ie": "utf8"},
            )
            if resp.status_code == 200:
                items = self._parse_sogou(resp.text)
                if items:
                    return items[: self.count]

            # 所有方式失败 → 降级
            return self._fallback()

    def _parse_sogou(self, html: str) -> List[BriefingItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[BriefingItem] = []
        seen: set[str] = set()

        for li in soup.select("ul.news-list > li, .txt-box, .news-box"):
            title_el = li.select_one("h3 a, h4 a, .txt-info a, a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if not title or len(title) < 6 or title in seen:
                continue
            seen.add(title)

            url = href if href.startswith("http") else f"https://weixin.sogou.com{href}"
            desc_el = li.select_one("p.txt-info, .txt-desc, p")
            summary = desc_el.get_text(strip=True)[:100] if desc_el else ""

            items.append(
                BriefingItem(title=title, url=url, summary=summary, source=self.name)
            )
            if len(items) >= self.count:
                break

        # 备用解析：直接找标题链接
        if not items:
            for a in soup.select("a[href]"):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if (
                    not title
                    or len(title) < 10
                    or title in seen
                    or "sogou.com" in href
                    or not href
                ):
                    continue
                if "weixin" not in href and "mp.weixin" not in href and "article" not in href:
                    continue
                seen.add(title)
                items.append(
                    BriefingItem(title=title, url=href, summary="", source=self.name)
                )
                if len(items) >= self.count:
                    break

        return items

    @staticmethod
    def _fallback() -> List[BriefingItem]:
        return [
            BriefingItem(
                title="访问新智元获取最新 AI 资讯",
                url="https://weixin.sogou.com/weixin?type=1&query=%E6%96%B0%E6%99%BA%E5%85%83",
                summary="新智元 — 微信公众号 AI 产业新媒体",
                source="新智元",
            )
        ]
