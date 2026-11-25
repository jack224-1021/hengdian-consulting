"""
恒典管理顧問有限公司 — 品牌社群視覺小卡產生器 (1080x1350, 4:5)
支援 checklist / comparison / qa 三種版型，配色與字體對齊官網 (#FAF8F4 / #1B3B36 / #A67C52)。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _load_font(font_path: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(font_path, size=size)
    if weight is not None:
        try:
            axes = font.get_variation_axes()
            if axes:
                # Noto VF uses wght axis (100..900)
                clamped = max(axes[0]["minimum"], min(axes[0]["maximum"], weight))
                font.set_variation_by_axes([clamped])
        except Exception:
            pass
    return font


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """精準像素寬度換行，支援中英文混排與手動換行符號。"""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            candidate = current + ch
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def generate_card(
    topic: dict[str, Any],
    settings: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """產製 1080x1350 品牌視覺小卡 PNG 並回傳儲存路徑。"""
    brand = settings["brand"]
    vc = settings["visual_card"]

    W = int(vc["width"])
    H = int(vc["height"])

    c_bg = _hex_to_rgb(vc["bg_cream"])
    c_white = _hex_to_rgb(vc["panel_white"])
    c_green = _hex_to_rgb(vc["primary_green"])
    c_gold = _hex_to_rgb(vc["accent_gold"])
    c_dark = _hex_to_rgb(vc["text_dark"])
    c_muted = _hex_to_rgb(vc["text_muted"])
    c_border = _hex_to_rgb(vc["border_sand"])
    c_grid = (237, 232, 223)
    c_gold_soft = (244, 236, 226)
    c_green_soft = (234, 241, 239)

    serif_path = vc["serif_font"]
    sans_path = vc["sans_font"]

    # 字體配置
    f_brand_zh = _load_font(serif_path, 30, weight=700)
    f_brand_en = _load_font(sans_path, 16, weight=600)
    f_tag = _load_font(sans_path, 24, weight=700)
    f_headline = _load_font(serif_path, 52, weight=700)
    f_subhead = _load_font(sans_path, 26, weight=500)
    f_pt_title = _load_font(sans_path, 29, weight=700)
    f_pt_desc = _load_font(sans_path, 23, weight=400)
    f_cta_label = _load_font(sans_path, 27, weight=700)
    f_footer_info = _load_font(sans_path, 23, weight=600)
    f_footer_sub = _load_font(sans_path, 19, weight=400)

    img = Image.new("RGB", (W, H), c_bg)
    draw = ImageDraw.Draw(img)

    # 1. 極淡工程製圖格線背景（提升工程顧問品牌質感）
    grid_step = 54
    for x in range(0, W, grid_step):
        draw.line([(x, 118), (x, H - 190)], fill=c_grid, width=1)
    for y in range(118, H - 190, grid_step):
        draw.line([(0, y), (W, y)], fill=c_grid, width=1)

    # 2. 頂部品牌深綠橫幅
    header_h = 112
    draw.rectangle([(0, 0), (W, header_h)], fill=c_green)
    # 細金線飾條
    draw.rectangle([(0, header_h), (W, header_h + 6)], fill=c_gold)

    # 頂部左側：品牌名稱
    margin_x = 68
    draw.text((margin_x, 26), brand["company_name"], font=f_brand_zh, fill=c_white)
    draw.text((margin_x, 68), brand["english_name"], font=f_brand_en, fill=(214, 200, 178))

    # 頂部右側：標籤膠囊
    tag_text = topic.get("tag", "專業顧問專欄")
    tag_w = int(draw.textlength(tag_text, font=f_tag))
    pill_pad_x = 24
    pill_h = 44
    pill_x2 = W - margin_x
    pill_x1 = pill_x2 - tag_w - pill_pad_x * 2
    pill_y1 = (header_h - pill_h) // 2
    _draw_rounded_rect(
        draw,
        (pill_x1, pill_y1, pill_x2, pill_y1 + pill_h),
        radius=22,
        fill=c_gold,
    )
    draw.text((pill_x1 + pill_pad_x, pill_y1 + 8), tag_text, font=f_tag, fill=c_white)

    # 3. 主標題與副標題區
    cursor_y = header_h + 52
    content_w = W - margin_x * 2

    headline_lines = _wrap_text(draw, topic["headline"], f_headline, content_w)
    for line in headline_lines:
        draw.text((margin_x, cursor_y), line, font=f_headline, fill=c_green)
        cursor_y += 70

    cursor_y += 10
    sub_lines = _wrap_text(draw, topic["subheadline"], f_subhead, content_w)
    for line in sub_lines:
        draw.text((margin_x, cursor_y), line, font=f_subhead, fill=c_muted)
        cursor_y += 38

    # 金色分隔線
    cursor_y += 18
    draw.rectangle([(margin_x, cursor_y), (margin_x + 120, cursor_y + 5)], fill=c_gold)
    draw.rectangle([(margin_x + 120, cursor_y + 2), (W - margin_x, cursor_y + 3)], fill=c_border)
    cursor_y += 34

    # 4. 內容重點卡片區（動態計算每張卡片高度，確保絕不重疊或裁切）
    template = topic.get("template", "checklist")
    points = topic.get("points", [])[:3]

    footer_h = 196
    footer_y = H - footer_h
    available_h = footer_y - cursor_y - 28
    gap_y = 22

    # 先量測每個重點所需的實際行數
    card_inner_pad_x = 34
    card_inner_pad_y = 24
    accent_bar_w = 10
    text_left_offset = accent_bar_w + 26
    text_max_w = content_w - text_left_offset - card_inner_pad_x

    prepared_cards = []
    total_natural_h = 0
    for idx, pt in enumerate(points):
        title_lines = _wrap_text(draw, pt["title"], f_pt_title, text_max_w)
        desc_lines = _wrap_text(draw, pt["desc"], f_pt_desc, text_max_w)
        natural_h = (
            card_inner_pad_y * 2
            + len(title_lines) * 40
            + 8
            + len(desc_lines) * 34
        )
        prepared_cards.append((idx, title_lines, desc_lines, natural_h))
        total_natural_h += natural_h

    total_gaps = gap_y * max(0, len(prepared_cards) - 1)
    extra_space = max(0, available_h - total_natural_h - total_gaps)
    bonus_per_card = min(22, extra_space // max(1, len(prepared_cards)))

    for idx, title_lines, desc_lines, natural_h in prepared_cards:
        card_h = natural_h + bonus_per_card
        x1, y1 = margin_x, cursor_y
        x2, y2 = W - margin_x, cursor_y + card_h

        # 卡片底陰影
        _draw_rounded_rect(
            draw,
            (x1 + 4, y1 + 6, x2 + 4, y2 + 6),
            radius=18,
            fill=(226, 220, 210),
        )

        # 依版型做細緻配色區分
        if template == "comparison":
            bar_color = c_green if idx == 0 else (c_gold if idx == 1 else (178, 72, 56))
            card_fill = c_white if idx < 2 else c_gold_soft
        elif template == "qa":
            bar_color = c_gold if idx % 2 == 0 else c_green
            card_fill = c_white
        else:  # checklist
            bar_color = c_green if idx % 2 == 0 else c_gold
            card_fill = c_white

        _draw_rounded_rect(
            draw,
            (x1, y1, x2, y2),
            radius=18,
            fill=card_fill,
            outline=c_border,
            width=2,
        )

        # 左側色條
        _draw_rounded_rect(
            draw,
            (x1 + 14, y1 + 18, x1 + 14 + accent_bar_w, y2 - 18),
            radius=5,
            fill=bar_color,
        )

        # 垂直置中文字區塊
        inner_text_h = len(title_lines) * 40 + 8 + len(desc_lines) * 34
        ty = y1 + (card_h - inner_text_h) // 2
        tx = x1 + 14 + text_left_offset

        for t_line in title_lines:
            draw.text((tx, ty), t_line, font=f_pt_title, fill=c_green if bar_color != (178, 72, 56) else (150, 48, 36))
            ty += 40
        ty += 8
        for d_line in desc_lines:
            draw.text((tx, ty), d_line, font=f_pt_desc, fill=c_dark)
            ty += 34

        cursor_y = y2 + gap_y

    # 5. 底部 CTA 與聯絡資訊深綠區
    draw.rectangle([(0, footer_y), (W, H)], fill=c_green)
    draw.rectangle([(0, footer_y), (W, footer_y + 6)], fill=c_gold)

    cta_text = topic.get("cta_label", "免費書面初判・歡迎線上諮詢")
    # CTA 膠囊條
    cta_pill_y1 = footer_y + 26
    cta_pill_y2 = cta_pill_y1 + 54
    _draw_rounded_rect(
        draw,
        (margin_x, cta_pill_y1, W - margin_x, cta_pill_y2),
        radius=27,
        fill=c_gold,
    )
    cta_w = draw.textlength(cta_text, font=f_cta_label)
    draw.text(((W - cta_w) / 2, cta_pill_y1 + 11), cta_text, font=f_cta_label, fill=c_white)

    # 聯絡資訊列（LINE + 電話 + 服務範圍）
    contact_line = f"官方 LINE：{brand['line_id']}   ｜   專線：{brand['phone']}   ｜   統編：{brand['tax_id']}"
    cl_w = draw.textlength(contact_line, font=f_footer_info)
    draw.text(((W - cl_w) / 2, footer_y + 98), contact_line, font=f_footer_info, fill=c_white)

    service_line = f"{brand['service_area']}  ・  {brand['website_url']}"
    sl_w = draw.textlength(service_line, font=f_footer_sub)
    draw.text(((W - sl_w) / 2, footer_y + 140), service_line, font=f_footer_sub, fill=(214, 200, 178))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    return out
