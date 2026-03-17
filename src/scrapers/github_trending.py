from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper, BriefingItem

TRENDING_URL = "https://github.com/trending"


class GitHubTrendingScraper(BaseScraper):
    name = "GitHub Trending"
    icon = "⭐"
    color = "#238636"

    async def fetch(self) -> List[BriefingItem]:
        async with self._client() as client:
            resp = await client.get(TRENDING_URL)
            resp.raise_for_status()
            return self._parse(resp.text)

    def _parse(self, html: str) -> List[BriefingItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[BriefingItem] = []

        rows = soup.select("article.Box-row")
        for row in rows[: self.count]:
            name_el = row.select_one("h2 a")
            if not name_el:
                continue
            repo_path = name_el.get("href", "").strip()
            repo_name = "/".join(p.strip() for p in repo_path.split("/") if p.strip())

            desc_el = row.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            stars_el = row.select_one("a.Link--muted[href$='/stargazers']")
            stars_text = stars_el.get_text(strip=True) if stars_el else ""

            lang_el = row.select_one("[itemprop='programmingLanguage']")
            lang = lang_el.get_text(strip=True) if lang_el else ""

            today_el = row.select_one("span.d-inline-block.float-sm-right")
            today_stars = today_el.get_text(strip=True) if today_el else ""

            summary_parts = []
            if lang:
                summary_parts.append(lang)
            if stars_text:
                summary_parts.append(f"★ {stars_text}")
            if today_stars:
                summary_parts.append(today_stars)

            items.append(
                BriefingItem(
                    title=repo_name,
                    url=f"https://github.com{repo_path}",
                    summary=" · ".join(summary_parts) if summary_parts else description,
                    score=self._parse_stars(stars_text),
                    source=self.name,
                )
            )
        return items

    @staticmethod
    def _parse_stars(text: str) -> int | None:
        if not text:
            return None
        cleaned = text.replace(",", "").strip()
        try:
            return int(cleaned)
        except ValueError:
            return None
