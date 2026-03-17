from .base import BaseScraper, BriefingItem, BriefingSection
from .jiqizhixin import JiqizhixinScraper
from .xinzhiyuan import XinzhiyuanScraper
from .qbitai import QbitAIScraper
from .aitop100 import AiTop100Scraper
from .github_trending import GitHubTrendingScraper

ALL_SCRAPERS = {
    "jiqizhixin": JiqizhixinScraper,
    "xinzhiyuan": XinzhiyuanScraper,
    "qbitai": QbitAIScraper,
    "aitop100": AiTop100Scraper,
    "github_trending": GitHubTrendingScraper,
}

__all__ = [
    "BaseScraper",
    "BriefingItem",
    "BriefingSection",
    "ALL_SCRAPERS",
    "JiqizhixinScraper",
    "XinzhiyuanScraper",
    "QbitAIScraper",
    "AiTop100Scraper",
    "GitHubTrendingScraper",
]
