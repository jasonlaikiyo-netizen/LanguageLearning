#!/usr/bin/env python3
"""每日從題庫抽 10 句,更新三頁 Markdown 與 README,並(選擇性)寄出 Email 通知。"""
import json
import os
import smtplib
from datetime import date, datetime
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "data" / "phrases_bank.json"
PER_DAY = 10
ANCHOR = date(2026, 1, 1)  # 輪播起算日

LANGS = {
    "english":  {"file": "english.md",  "title": "每日英語口語短句", "flag": "🇺🇸", "name": "English", "col": None},
    "japanese": {"file": "japanese.md", "title": "每日日語口語短句", "flag": "🇯🇵", "name": "日本語", "col": "羅馬拼音 (Romaji)"},
    "thai":     {"file": "thai.md",     "title": "每日泰語口語短句", "flag": "🇹🇭", "name": "ภาษาไทย", "col": "羅馬拼音 (Romanization)"},
}


def pick(items, today):
    """依日期輪播:每天往後移 10 句,題庫用完自動從頭循環。"""
    n = len(items)
    start = ((today - ANCHOR).days * PER_DAY) % n
    return [items[(start + i) % n] for i in range(PER_DAY)]


def render_page(cfg, phrases, today):
    lines = [f"# {cfg['flag']} {cfg['title']}", "", f"📅 {today.isoformat()}", ""]
    if cfg["col"]:
        lines += [f"| # | 中文 | {cfg['name']} | {cfg['col']} |", "|---|------|------|------|"]
        for i, p in enumerate(phrases, 1):
            lines.append(f"| {i} | {p['zh']} | {p['text']} | {p['romaji']} |")
    else:
        lines += ["| # | 中文 | English |", "|---|------|---------|"]
        for i, p in enumerate(phrases, 1):
            lines.append(f"| {i} | {p['zh']} | {p['text']} |")
    lines += ["", "[← 回首頁](README.md)", ""]
    return "\n".join(lines)


def render_readme(today):
    return f"""# 📚 每日口語短句

每天自動更新英語、日語、泰語各 10 句口語短句。

最後更新:**{today.isoformat()}**

| 語言 | 連結 |
|------|------|
| 🇺🇸 英語 | [english.md](english.md) |
| 🇯🇵 日語 | [japanese.md](japanese.md) |
| 🇹🇭 泰語 | [thai.md](thai.md) |
"""


def send_email(subject, body):
    user = os.environ.get("GMAIL_USER")
    pwd = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("MAIL_TO") or user
    if not (user and pwd):
        print("未設定 GMAIL_USER / GMAIL_APP_PASSWORD,略過 Email 通知。")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print("Email 已寄出。")


def main():
    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    mail_parts = []
    for key, cfg in LANGS.items():
        phrases = pick(bank[key], today)
        (ROOT / cfg["file"]).write_text(render_page(cfg, phrases, today), encoding="utf-8")
        block = [f"{cfg['flag']} {cfg['title']}"]
        for i, p in enumerate(phrases, 1):
            romaji = f" ({p['romaji']})" if "romaji" in p else ""
            block.append(f"{i}. {p['text']}{romaji}\n   {p['zh']}")
        mail_parts.append("\n".join(block))
    (ROOT / "README.md").write_text(render_readme(today), encoding="utf-8")
    send_email(f"📚 {today.isoformat()} 每日口語短句", "\n\n".join(mail_parts))


if __name__ == "__main__":
    main()
