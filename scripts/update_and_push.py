#!/usr/bin/env python3
"""每日從題庫抽 10 句,更新三頁 Markdown、三份獨立的 A4 PDF(每個語言一份),並寄出 Email。"""
import html
import json
import os
import smtplib
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "data" / "phrases_bank.json"
PDF_DIR = ROOT / "pdf"
PER_DAY = 10
ANCHOR = date(2026, 1, 1)  # 輪播起算日

LANGS = {
    "english":  {"file": "english.md",  "title": "每日英語口語短句", "sub": "English",  "flag": "🇺🇸", "lang": "en"},
    "japanese": {"file": "japanese.md", "title": "每日日語口語短句", "sub": "日本語",   "flag": "🇯🇵", "lang": "ja"},
    "thai":     {"file": "thai.md",     "title": "每日泰語口語短句", "sub": "ภาษาไทย", "flag": "🇹🇭", "lang": "th"},
}


def pick(items, today):
    """依日期輪播:每天往後移 10 句,題庫用完自動從頭循環。"""
    n = len(items)
    start = ((today - ANCHOR).days * PER_DAY) % n
    return [items[(start + i) % n] for i in range(PER_DAY)]


# ---------- Markdown ----------
def render_md(cfg, phrases, today):
    lines = [f"# {cfg['flag']} {cfg['title']}", "", f"📅 {today.isoformat()}", ""]
    for i, p in enumerate(phrases, 1):
        lines.append(f"### {i}. {p['text']}")
        if p.get("romaji"):
            lines.append(f"- 發音:{p['romaji']}")
        lines.append(f"- 中文:{p['zh']}")
        lines.append(f"- 使用時機:{p['when']}")
        lines.append(f"- 例句:{p['ex']}")
        if p.get("ex_romaji"):
            lines.append(f"  - 發音:{p['ex_romaji']}")
        lines.append(f"  - 翻譯:{p['ex_zh']}")
        lines.append("")
    lines += ["[← 回首頁](README.md)", ""]
    return "\n".join(lines)


def render_readme(today, pdfs):
    def link(key):
        return f"[PDF](" + f"{key}.pdf)" if key in pdfs else "-"
    return f"""# 📚 每日口語短句

每天自動更新英語、日語、泰語各 10 句口語短句,附使用時機與例句。

最後更新:**{today.isoformat()}**

| 語言 | 網頁 | A4 PDF(可列印) |
|------|------|------|
| 🇺🇸 英語 | [english.md](english.md) | {link("english")} |
| 🇯🇵 日語 | [japanese.md](japanese.md) | {link("japanese")} |
| 🇹🇭 泰語 | [thai.md](thai.md) | {link("thai")} |
"""


# ---------- PDF (A4, 每個語言一頁) ----------
def pdf_css(k):
    """k 為縮放倍率;字級與間距都乘上 k,讓內容剛好排滿 A4。"""
    f = lambda v: f"{v * k:.2f}pt"
    m = lambda v: f"{v * k:.2f}mm"
    return f"""
@page {{ size: A4; margin: 11mm 12mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Noto Sans CJK TC', 'Noto Sans TC', sans-serif; font-size: {f(9.5)}; color: #222; margin: 0; }}
section.page {{ page-break-after: always; }}
section.page:last-child {{ page-break-after: auto; }}
.head {{ display: flex; justify-content: space-between; align-items: baseline;
        border-bottom: 2px solid #333; padding-bottom: 2mm; margin-bottom: 1mm; }}
.head h1 {{ font-size: 15pt; margin: 0; }}
.head .date {{ font-size: 9pt; color: #666; }}
table {{ width: 100%; border-collapse: collapse; }}
td {{ vertical-align: top; padding: {m(2.5)} 1.5mm; border-bottom: 0.5pt solid #ccc; }}
td.no {{ width: 6mm; color: #999; font-size: 9pt; }}
td.phrase {{ width: 38%; padding-right: 3mm; }}
.t {{ font-size: {f(12.5)}; font-weight: bold; line-height: 1.35; }}
.r {{ font-size: {f(9)}; color: #555; margin-top: 0.6mm; }}
.z {{ font-size: {f(9.5)}; margin-top: 0.6mm; }}
.w {{ font-size: {f(9)}; color: #444; line-height: 1.4; }}
.w b {{ color: #1a5fb4; }}
.e {{ margin-top: 1mm; padding: 1mm 2mm; background: #f3f5f8; border-left: 2pt solid #1a5fb4; }}
.e .xt {{ font-size: {f(10)}; line-height: 1.4; }}
.e .xr {{ font-size: {f(8.5)}; color: #555; }}
.e .xz {{ font-size: {f(9)}; color: #333; }}
.lang-ja .t, .lang-ja .xt {{ font-family: 'Noto Sans CJK JP', 'Noto Sans CJK TC', sans-serif; }}
.lang-th .t, .lang-th .xt {{ font-family: 'Noto Sans Thai', 'Loma', 'Garuda', 'Noto Sans CJK TC', sans-serif; }}
"""


def pdf_section(cfg, phrases, today):
    e = html.escape
    rows = []
    for i, p in enumerate(phrases, 1):
        romaji = f'<div class="r">{e(p["romaji"])}</div>' if p.get("romaji") else ""
        ex_romaji = f'<div class="xr">{e(p["ex_romaji"])}</div>' if p.get("ex_romaji") else ""
        rows.append(
            f'<tr><td class="no">{i}</td>'
            f'<td class="phrase"><div class="t">{e(p["text"])}</div>{romaji}<div class="z">{e(p["zh"])}</div></td>'
            f'<td><div class="w"><b>使用時機</b>　{e(p["when"])}</div>'
            f'<div class="e"><div class="xt">{e(p["ex"])}</div>{ex_romaji}<div class="xz">{e(p["ex_zh"])}</div></div></td></tr>'
        )
    return (
        f'<section class="page lang-{cfg["lang"]}" lang="{cfg["lang"]}">'
        f'<div class="head"><h1>{e(cfg["title"])} · {e(cfg["sub"])}</h1><div class="date">{today.isoformat()}</div></div>'
        f'<table>{"".join(rows)}</table></section>'
    )


def build_pdf(key, section_html):
    """每個語言各產一份 A4 PDF。優先縮放到剛好一頁;排不下就用標準字級,允許多頁。"""
    from weasyprint import HTML  # 延後載入:沒安裝時只會略過 PDF,不影響其他功能

    def render(k):
        return HTML(string=f"<html><head><meta charset='utf-8'><style>{pdf_css(k)}</style></head>"
                           f"<body>{section_html}</body></html>").render()

    doc = None
    for k in (1.1, 1.05, 1.0, 0.95, 0.9):
        cand = render(k)
        if len(cand.pages) == 1:
            doc = cand
            break
    if doc is None:
        doc = render(1.0)
    path = ROOT / f"{key}.pdf"
    doc.write_pdf(str(path))
    print(f"{path.name}:{len(doc.pages)} 頁")
    return path


# ---------- Email ----------
def send_email(subject, body, attachments=(), date_str=""):
    user = os.environ.get("GMAIL_USER")
    pwd = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("MAIL_TO") or user
    if not (user and pwd):
        print("未設定 GMAIL_USER / GMAIL_APP_PASSWORD,略過 Email 通知。")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.set_content(body)
    for path in attachments:
        path = Path(path)
        msg.add_attachment(path.read_bytes(), maintype="application", subtype="pdf",
                           filename=f"{path.stem}_{date_str}.pdf")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print("Email 已寄出。")


def main():
    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    mail_parts, pdfs = [], {}

    for key, cfg in LANGS.items():
        phrases = pick(bank[key], today)
        (ROOT / cfg["file"]).write_text(render_md(cfg, phrases, today), encoding="utf-8")
        try:
            pdfs[key] = build_pdf(key, pdf_section(cfg, phrases, today))
        except Exception as e:  # PDF 失敗不影響頁面更新
            print(f"{key} PDF 產生失敗,略過:{e}")
        block = [f"{cfg['flag']} {cfg['title']}"]
        for i, p in enumerate(phrases, 1):
            romaji = f" ({p['romaji']})" if p.get("romaji") else ""
            block.append(f"{i}. {p['text']}{romaji}\n   {p['zh']}")
        mail_parts.append("\n".join(block))

    (ROOT / "README.md").write_text(render_readme(today, pdfs), encoding="utf-8")

    body = "\n\n".join(mail_parts)
    if pdfs:
        body += "\n\n📎 附件為 A4 版 PDF:每個語言一份,含使用時機與例句,可直接列印。"
    try:
        send_email(f"📚 {today.isoformat()} 每日口語短句", body, list(pdfs.values()))
    except Exception as e:  # 寄信失敗不擋住後面的 commit
        print(f"Email 寄送失敗,略過:{e}")


if __name__ == "__main__":
    main()
