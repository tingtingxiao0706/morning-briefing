from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

import httpx
from loguru import logger

from src.scrapers.base import BriefingSection

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuNotifier:
    def __init__(self, app_id: str, app_secret: str, chat_id: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self._token: str | None = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu auth failed: {data.get('msg')}")
            self._token = data["tenant_access_token"]
            logger.success("Feishu tenant_access_token acquired")
            return self._token

    async def _upload_image(self, image_path: Path) -> str:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as client:
            with open(image_path, "rb") as f:
                resp = await client.post(
                    f"{FEISHU_BASE}/im/v1/images",
                    headers={"Authorization": f"Bearer {token}"},
                    data={"image_type": "message"},
                    files={"image": (image_path.name, f, "image/png")},
                )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu image upload failed: {data.get('msg')}")
            image_key = data["data"]["image_key"]
            logger.success(f"Image uploaded to Feishu: {image_key}")
            return image_key

    async def _send_message(self, msg_type: str, content: dict) -> bool:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{FEISHU_BASE}/im/v1/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"receive_id_type": "chat_id"},
                json={
                    "receive_id": self.chat_id,
                    "msg_type": msg_type,
                    "content": json.dumps(content),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"Feishu send failed: {data.get('msg')}")
                return False
            return True

    async def send(
        self,
        sections: List[BriefingSection],
        image_path: Path,
        html_path: Path | None = None,
        report_url: str | None = None,
    ) -> bool:
        await self._get_token()

        # 1. 发送图片（预览）
        image_key = await self._upload_image(image_path)
        ok = await self._send_message("image", {"image_key": image_key})
        if not ok:
            return False
        logger.success("Feishu image sent")

        # 2. 发送可点击的报告链接
        if report_url:
            date_str = datetime.now().strftime("%Y-%m-%d")
            post_content = {
                "zh_cn": {
                    "title": f"☀ 晨间简报 · {date_str}",
                    "content": [
                        [
                            {"tag": "text", "text": "👆 点击图片可放大查看\n\n"},
                        ],
                        [
                            {"tag": "a", "text": "📖 打开完整报告（链接可点击）", "href": report_url},
                        ],
                    ],
                }
            }
            ok = await self._send_message("post", post_content)
            if ok:
                logger.success(f"Feishu report link sent: {report_url}")

        return True
