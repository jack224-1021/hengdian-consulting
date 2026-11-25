"""
Meta 官方 API 自動發文模組
支援：
1. Facebook 粉絲專頁 (Graph API v21.0: /{page_id}/photos)
2. Instagram 商業帳號 (Graph API v21.0: /{ig_user_id}/media -> media_publish)
3. Threads 官方 API (graph.threads.net/v1.0: /{threads_user_id}/threads -> threads_publish)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class PublishResult:
    platform: str
    status: str  # "published" | "dry_run" | "skipped" | "error"
    post_id: str | None = None
    detail: str = ""


class MetaPublisher:
    def __init__(self, settings: dict[str, Any]) -> None:
        meta_cfg = settings.get("meta_api", {})
        self.graph_version = meta_cfg.get("graph_version", "v21.0")
        self.graph_base = f"https://graph.facebook.com/{self.graph_version}"
        self.threads_base = meta_cfg.get("threads_base_url", "https://graph.threads.net/v1.0")

        self.fb_page_id = os.getenv("FB_PAGE_ID", "").strip()
        self.fb_page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
        self.ig_user_id = os.getenv("IG_USER_ID", "").strip()
        self.threads_user_id = os.getenv("THREADS_USER_ID", "").strip()
        self.threads_token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()

    def credential_status(self) -> dict[str, bool]:
        return {
            "facebook": bool(self.fb_page_id and self.fb_page_token),
            "instagram": bool(self.ig_user_id and self.fb_page_token),
            "threads": bool(self.threads_user_id and self.threads_token),
        }

    def publish_facebook(
        self,
        message: str,
        image_url: str,
        dry_run: bool = True,
    ) -> PublishResult:
        if dry_run:
            return PublishResult(
                platform="facebook",
                status="dry_run",
                detail=f"[預覽模式] 準備發送圖片貼文至 FB 粉專 ({self.fb_page_id or '尚未設定 FB_PAGE_ID'})，圖片網址：{image_url}",
            )
        if not (self.fb_page_id and self.fb_page_token):
            return PublishResult(
                platform="facebook",
                status="skipped",
                detail="缺少 FB_PAGE_ID 或 FB_PAGE_ACCESS_TOKEN，請先參考 META_API_SETUP_GUIDE.md 填入 .env。",
            )

        url = f"{self.graph_base}/{self.fb_page_id}/photos"
        payload = {
            "url": image_url,
            "caption": message,
            "access_token": self.fb_page_token,
        }
        try:
            resp = requests.post(url, data=payload, timeout=30)
            data = resp.json()
            if resp.ok and ("id" in data or "post_id" in data):
                pid = str(data.get("post_id") or data.get("id"))
                return PublishResult(platform="facebook", status="published", post_id=pid, detail="Facebook 粉專發文成功")
            return PublishResult(platform="facebook", status="error", detail=f"HTTP {resp.status_code}: {data}")
        except Exception as exc:
            return PublishResult(platform="facebook", status="error", detail=str(exc))

    def publish_instagram(
        self,
        caption: str,
        image_url: str,
        dry_run: bool = True,
    ) -> PublishResult:
        if dry_run:
            return PublishResult(
                platform="instagram",
                status="dry_run",
                detail=f"[預覽模式] 準備建立 IG 圖片貼文 ({self.ig_user_id or '尚未設定 IG_USER_ID'})，圖片網址：{image_url}",
            )
        if not (self.ig_user_id and self.fb_page_token):
            return PublishResult(
                platform="instagram",
                status="skipped",
                detail="缺少 IG_USER_ID 或 FB_PAGE_ACCESS_TOKEN，請先參考 META_API_SETUP_GUIDE.md 填入 .env。",
            )

        try:
            # Step 1: 建立 Media Container
            create_url = f"{self.graph_base}/{self.ig_user_id}/media"
            r1 = requests.post(
                create_url,
                data={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": self.fb_page_token,
                },
                timeout=30,
            )
            d1 = r1.json()
            if not (r1.ok and "id" in d1):
                return PublishResult(platform="instagram", status="error", detail=f"建立容器失敗: {d1}")
            creation_id = d1["id"]

            # 等待 Meta 抓取圖片完成
            time.sleep(4)

            # Step 2: 正式發布
            pub_url = f"{self.graph_base}/{self.ig_user_id}/media_publish"
            r2 = requests.post(
                pub_url,
                data={
                    "creation_id": creation_id,
                    "access_token": self.fb_page_token,
                },
                timeout=30,
            )
            d2 = r2.json()
            if r2.ok and "id" in d2:
                return PublishResult(platform="instagram", status="published", post_id=str(d2["id"]), detail="Instagram 發文成功")
            return PublishResult(platform="instagram", status="error", detail=f"發布失敗: {d2}")
        except Exception as exc:
            return PublishResult(platform="instagram", status="error", detail=str(exc))

    def publish_threads(
        self,
        text: str,
        image_url: str,
        dry_run: bool = True,
    ) -> PublishResult:
        if dry_run:
            return PublishResult(
                platform="threads",
                status="dry_run",
                detail=f"[預覽模式] 準備發送 Threads 圖文貼文 ({self.threads_user_id or '尚未設定 THREADS_USER_ID'})，圖片網址：{image_url}",
            )
        if not (self.threads_user_id and self.threads_token):
            return PublishResult(
                platform="threads",
                status="skipped",
                detail="缺少 THREADS_USER_ID 或 THREADS_ACCESS_TOKEN，請先參考 META_API_SETUP_GUIDE.md 填入 .env。",
            )

        try:
            # Step 1: 建立 Threads Container
            create_url = f"{self.threads_base}/{self.threads_user_id}/threads"
            r1 = requests.post(
                create_url,
                data={
                    "media_type": "IMAGE",
                    "image_url": image_url,
                    "text": text,
                    "access_token": self.threads_token,
                },
                timeout=30,
            )
            d1 = r1.json()
            if not (r1.ok and "id" in d1):
                return PublishResult(platform="threads", status="error", detail=f"建立 Threads 容器失敗: {d1}")
            creation_id = d1["id"]

            time.sleep(4)

            # Step 2: 正式發布
            pub_url = f"{self.threads_base}/{self.threads_user_id}/threads_publish"
            r2 = requests.post(
                pub_url,
                data={
                    "creation_id": creation_id,
                    "access_token": self.threads_token,
                },
                timeout=30,
            )
            d2 = r2.json()
            if r2.ok and "id" in d2:
                return PublishResult(platform="threads", status="published", post_id=str(d2["id"]), detail="Threads 發文成功")
            return PublishResult(platform="threads", status="error", detail=f"發布失敗: {d2}")
        except Exception as exc:
            return PublishResult(platform="threads", status="error", detail=str(exc))
