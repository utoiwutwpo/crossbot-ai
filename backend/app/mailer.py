"""
邮件发送（SMTP）。未配置 SMTP_HOST 时所有发送静默跳过，不影响主流程。
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import settings

log = logging.getLogger("crossbot.mail")


def send_email(to: str, subject: str, html: str) -> bool:
    if not settings.smtp_host:
        log.info("SMTP 未配置，跳过邮件：%s | %s", to, subject)
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))
    if settings.smtp_ssl:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        server.starttls()
    try:
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(msg["From"], [to], msg.as_string())
        return True
    finally:
        server.quit()
