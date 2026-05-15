import os
import smtplib
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.mime.text import MIMEText
from html import unescape


def get_env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def fetch_ai_news() -> list[dict[str, str]]:
    lang = get_env("NEWS_LANG", "zh-CN")
    region = "CN" if lang.lower().startswith("zh") else "US"
    query = urllib.parse.quote("AI when:1d")
    url = (
        f"https://news.google.com/rss/search?q={query}"
        f"&hl={lang}&gl={region}&ceid={region}:{lang}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = resp.read()

    root = ET.fromstring(payload)
    items = []
    for node in root.findall("./channel/item")[:20]:
        items.append(
            {
                "title": unescape((node.findtext("title") or "").strip()),
                "link": (node.findtext("link") or "").strip(),
                "pubDate": (node.findtext("pubDate") or "").strip(),
            }
        )
    return items


def summarize_with_copilot(news_items: list[dict[str, str]]) -> str:
    if not news_items:
        return "最近24小时未检索到符合条件的 AI 新闻。"

    lines = [
        f"{i + 1}. {item['title']} ({item['pubDate']})\n{item['link']}"
        for i, item in enumerate(news_items)
    ]
    prompt = (
        "请根据以下最近24小时AI新闻，输出中文邮件正文：\n"
        "1) 先给3-5条总体趋势总结\n"
        "2) 再给不超过10条重点新闻，每条包含一句解读\n"
        "3) 最后给一句对从业者的建议\n\n"
        + "\n\n".join(lines)
    )

    model = get_env("COPILOT_MODEL", "gpt-5-mini")
    cmd = ["gh", "copilot", "-p", prompt, "--silent", "--model", model]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    summary = result.stdout.strip()
    if result.returncode == 0 and summary:
        return summary

    fallback = "\n".join([f"- {item['title']} ({item['link']})" for item in news_items[:10]])
    return (
        "Copilot 摘要生成失败，以下为新闻列表（请检查 COPILOT_GH_TOKEN 或模型权限）：\n\n"
        + fallback
    )


def send_mail(content: str) -> None:
    email_from = get_env("EMAIL_FROM")
    email_to = get_env("EMAIL_TO")
    smtp_host = get_env("SMTP_HOST")
    smtp_port = int(get_env("SMTP_PORT", "465"))
    smtp_user = get_env("SMTP_USERNAME")
    smtp_password = get_env("SMTP_PASSWORD")
    use_tls = get_env("SMTP_USE_TLS", "true").lower() != "false"

    missing = [
        name
        for name, value in {
            "EMAIL_FROM": email_from,
            "EMAIL_TO": email_to,
            "SMTP_HOST": smtp_host,
            "SMTP_USERNAME": smtp_user,
            "SMTP_PASSWORD": smtp_password,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")

    subject = f"AI 新闻日报 - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to

    if use_tls:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, [addr.strip() for addr in email_to.split(",")], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, [addr.strip() for addr in email_to.split(",")], msg.as_string())


def main() -> None:
    news_items = fetch_ai_news()
    summary = summarize_with_copilot(news_items)
    send_mail(summary)


if __name__ == "__main__":
    main()
