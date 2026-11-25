"""
恒典管理顧問有限公司 — 每週業務推廣一鍵產圖＆自動發文主程式

使用方式：
  1. 預覽模式（預設，不實際發文，產出小卡圖檔＋4平台文案＋preview.html）：
     python run_weekly_post.py --dry-run
     python run_weekly_post.py --topic W01_outflow_2ha --dry-run

  2. 正式發布模式（推送小卡至 GitHub Pages 並呼叫 Meta API 自動發佈 FB/IG/Threads）：
     python run_weekly_post.py --publish
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))

from src.card_generator import generate_card  # noqa: E402
from src.meta_publisher import MetaPublisher, PublishResult  # noqa: E402


def load_settings() -> dict[str, Any]:
    with (BASE_DIR / "config" / "settings.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_topics() -> list[dict[str, Any]]:
    with (BASE_DIR / "config" / "topics.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def load_history() -> list[dict[str, Any]]:
    hist_file = BASE_DIR / "state" / "publish_history.json"
    if not hist_file.exists():
        return []
    with hist_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_history(records: list[dict[str, Any]]) -> None:
    hist_file = BASE_DIR / "state" / "publish_history.json"
    hist_file.parent.mkdir(parents=True, exist_ok=True)
    with hist_file.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def pick_topic(topics: list[dict[str, Any]], history: list[dict[str, Any]], requested_id: str | None) -> dict[str, Any]:
    if requested_id:
        for t in topics:
            if t["id"] == requested_id:
                return t
        raise SystemExit(f"找不到指定主題 ID：{requested_id}")

    published_ids = {r["topic_id"] for r in history if r.get("mode") == "publish"}
    for t in topics:
        if t["id"] not in published_ids:
            return t
    # 全部主題都發完一輪後，從頭輪播
    return topics[len(history) % len(topics)]


def write_preview_html(
    post_dir: Path,
    topic: dict[str, Any],
    public_image_url: str,
    results: list[PublishResult],
) -> Path:
    copy = topic["copy"]
    platforms = [
        ("facebook", "Facebook 粉絲專頁 / 社團", copy["facebook"]),
        ("instagram", "Instagram 商業帳號", copy["instagram"]),
        ("threads", "Threads 互動短文", copy["threads"]),
        ("google_business", "Google 商家檔案動態（手動貼上）", copy["google_business"]),
    ]

    blocks_html = []
    for key, label, text in platforms:
        escaped = html.escape(text)
        blocks_html.append(
            f"""
            <section class="copy-card">
              <div class="copy-header">
                <h3>{html.escape(label)}</h3>
                <button onclick="copyText('copy-{key}', this)">一鍵複製文案</button>
              </div>
              <pre id="copy-{key}">{escaped}</pre>
            </section>
            """
        )

    status_rows = "".join(
        f"<li><strong>{html.escape(r.platform.upper())}</strong>：[{html.escape(r.status)}] {html.escape(r.detail)}</li>"
        for r in results
    )

    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>恒典每週推廣預覽｜{html.escape(topic['id'])}</title>
  <style>
    body {{
      font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
      background: #FAF8F4;
      color: #1F2933;
      margin: 0;
      padding: 28px 18px 60px;
    }}
    .wrap {{ max-width: 1120px; margin: 0 auto; }}
    header {{
      background: #1B3B36;
      color: #fff;
      padding: 22px 28px;
      border-radius: 14px;
      border-bottom: 5px solid #A67C52;
      margin-bottom: 24px;
    }}
    header h1 {{ margin: 0 0 6px; font-size: 22px; }}
    header p {{ margin: 0; opacity: 0.88; font-size: 14px; }}
    .grid {{
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 24px;
      align-items: start;
    }}
    @media (max-width: 860px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    .card-box {{
      background: #fff;
      border: 1px solid #D8D0C3;
      border-radius: 14px;
      padding: 16px;
    }}
    .card-box img {{
      width: 100%;
      border-radius: 10px;
      display: block;
      border: 1px solid #E5E0D6;
    }}
    .meta-note {{
      font-size: 13px;
      color: #52606D;
      margin-top: 12px;
      word-break: break-all;
    }}
    .status-box {{
      background: #fff;
      border-left: 5px solid #A67C52;
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 18px;
      font-size: 14px;
    }}
    .status-box ul {{ margin: 8px 0 0; padding-left: 20px; }}
    .copy-card {{
      background: #fff;
      border: 1px solid #D8D0C3;
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 16px;
    }}
    .copy-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .copy-header h3 {{ margin: 0; font-size: 16px; color: #1B3B36; }}
    button {{
      background: #1B3B36;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 7px 14px;
      cursor: pointer;
      font-size: 13px;
    }}
    button:hover {{ background: #A67C52; }}
    pre {{
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
      font-size: 14px;
      line-height: 1.65;
      background: #FAF8F4;
      padding: 12px 14px;
      border-radius: 8px;
      margin: 0;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>恒典管理顧問有限公司｜每週業務推廣預覽</h1>
      <p>主題代號：{html.escape(topic['id'])}　｜　主軸：{html.escape(topic['pillar'])}　｜　標籤：{html.escape(topic['tag'])}</p>
    </header>
    <div class="grid">
      <div class="card-box">
        <img src="card.png" alt="{html.escape(topic['id'])}" />
        <div class="meta-note">
          <strong>公開圖片網址（供 IG / Threads API 讀取）：</strong><br />
          <a href="{html.escape(public_image_url)}" target="_blank">{html.escape(public_image_url)}</a>
        </div>
      </div>
      <div>
        <div class="status-box">
          <strong>執行狀態回報</strong>
          <ul>{status_rows}</ul>
        </div>
        {''.join(blocks_html)}
      </div>
    </div>
  </div>
  <script>
    function copyText(id, btn) {{
      const txt = document.getElementById(id).innerText;
      navigator.clipboard.writeText(txt).then(() => {{
        const orig = btn.innerText;
        btn.innerText = '已複製 ✓';
        setTimeout(() => btn.innerText = orig, 1600);
      }});
    }}
  </script>
</body>
</html>
"""
    preview_path = post_dir / "preview.html"
    preview_path.write_text(page, encoding="utf-8")
    return preview_path


def ensure_card_pushed_to_github_pages(card_path: Path, public_url: str) -> bool:
    """將新產製的小卡 PNG 推送至 GitHub Pages，並等待 HTTPS 網址可讀取。"""
    rel_card = card_path.relative_to(REPO_ROOT).as_posix()
    subprocess.run(["git", "add", rel_card], cwd=REPO_ROOT, check=False)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT)
    if diff.returncode != 0:
        subprocess.run(
            ["git", "commit", "-m", f"marketing: add weekly card {card_path.name}"],
            cwd=REPO_ROOT,
            check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)

    # 等待 GitHub Pages 上線（最長 60 秒）
    for _ in range(12):
        try:
            r = requests.head(public_url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="恒典管理顧問有限公司 — 每週業務推廣產圖＆發文工具")
    parser.add_argument("--topic", help="指定主題 ID（例如 W01_outflow_2ha），省略則自動挑選下一篇未發布主題")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="僅產圖與預覽，不實際發文（預設）")
    mode_group.add_argument("--publish", action="store_true", help="正式推送圖檔並呼叫 Meta API 自動發文")
    args = parser.parse_args()

    is_publish = bool(args.publish)
    dry_run = not is_publish

    load_dotenv(BASE_DIR / ".env")
    settings = load_settings()
    topics = load_topics()
    history = load_history()

    topic = pick_topic(topics, history, args.topic)
    today_str = datetime.now().strftime("%Y%m%d")

    # 1. 產製品牌視覺小卡 PNG
    card_path = BASE_DIR / "cards" / f"{topic['id']}.png"
    generate_card(topic, settings, card_path)
    print(f"[OK] 已產製視覺小卡：{card_path}")

    # 2. 建立本週輸出資料夾與各平台文案檔
    post_dir = BASE_DIR / "posts" / f"{today_str}_{topic['id']}"
    post_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(card_path, post_dir / "card.png")

    for platform_key in ("facebook", "instagram", "threads", "google_business"):
        (post_dir / f"{platform_key}.txt").write_text(
            topic["copy"][platform_key], encoding="utf-8"
        )

    base_url = settings["hosting"]["public_cards_base_url"].rstrip("/")
    public_image_url = f"{base_url}/{card_path.name}"

    # 3. 正式發布前先確保圖片已上線 GitHub Pages
    if is_publish and settings["hosting"].get("auto_git_push_cards", True):
        print(f"[INFO] 正在同步圖檔至 GitHub Pages：{public_image_url}")
        ok = ensure_card_pushed_to_github_pages(card_path, public_image_url)
        if not ok:
            print("[WARN] GitHub Pages 尚未回傳 HTTP 200，仍將嘗試送出（如 IG/Threads 抓圖失敗可稍後重試）。")

    # 4. 呼叫 Meta API（或執行 Dry-Run）
    publisher = MetaPublisher(settings)
    results = [
        publisher.publish_facebook(topic["copy"]["facebook"], public_image_url, dry_run=dry_run),
        publisher.publish_instagram(topic["copy"]["instagram"], public_image_url, dry_run=dry_run),
        publisher.publish_threads(topic["copy"]["threads"], public_image_url, dry_run=dry_run),
        PublishResult(
            platform="google_business",
            status="manual_ready",
            detail="Google 商家動態文案已輸出至 google_business.txt 與 preview.html，可一鍵複製貼上。",
        ),
    ]

    preview_path = write_preview_html(post_dir, topic, public_image_url, results)
    print(f"[OK] 已產出 4 平台文案與預覽頁：{preview_path}")

    for r in results:
        print(f"  - {r.platform.upper():15s} | {r.status:12s} | {r.detail}")

    # 5. 寫入歷史紀錄
    history.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "topic_id": topic["id"],
            "mode": "publish" if is_publish else "dry_run",
            "card_url": public_image_url,
            "results": [
                {"platform": r.platform, "status": r.status, "post_id": r.post_id, "detail": r.detail}
                for r in results
            ],
        }
    )
    save_history(history)
    print(f"[DONE] 執行紀錄已儲存至：{BASE_DIR / 'state' / 'publish_history.json'}")


if __name__ == "__main__":
    main()
