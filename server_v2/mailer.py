from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send(to: str, subject: str, text: str) -> bool:
    host=os.getenv("JANUS_SMTP_HOST","").strip(); password=os.getenv("JANUS_SMTP_PASSWORD","").strip()
    if not host or not password or not to: return False
    port=int(os.getenv("JANUS_SMTP_PORT","587")); user=os.getenv("JANUS_SMTP_USER","").strip()
    sender=os.getenv("JANUS_SMTP_FROM","JANUS <onboarding@resend.dev>").strip()
    try:
        msg=EmailMessage(); msg["From"]=sender; msg["To"]=to; msg["Subject"]=subject; msg.set_content(text)
        with smtplib.SMTP(host,port,timeout=20) as smtp:
            if os.getenv("JANUS_SMTP_TLS","1")=="1": smtp.starttls()
            if user: smtp.login(user,password)
            smtp.send_message(msg)
        return True
    except Exception:
        return False
