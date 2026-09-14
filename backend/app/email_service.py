import smtplib
import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from app.config import get_settings

settings = get_settings()


def _get_logo_base64() -> str:
    # Self-contained copy under app/static/ — the sibling Flutter-app backend
    # reaches across into teach_ai/assets/ for this; this project doesn't
    # depend on that repo at all, so the logo lives locally instead.
    path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


async def send_reset_code(email: str, code: str) -> bool:
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER
    password = settings.SMTP_PASSWORD
    from_name = settings.SMTP_FROM_NAME

    if not user or not password:
        print(f"\n{'='*50}")
        print(f"[PASSWORD RESET] Email: {email}")
        print(f"[PASSWORD RESET] Kod: {code}")
        print(f"[PASSWORD RESET] SMTP not configured — printed to console")
        print(f"{'='*50}\n")
        return True

    logo_b64 = _get_logo_base64()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{from_name} — Код восстановления пароля"
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="teachai.app")
    msg["X-Mailer"] = "Dastyor"
    msg["List-Unsubscribe"] = f"<mailto:{user}?subject=unsubscribe>"

    text = f"""
Код восстановления пароля Dastyor
Код: {code}
Действителен: 15 минут
    """.strip()

    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="Dastyor" style="height:48px;margin-bottom:16px">' if logo_b64 else ""

    html = f"""<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"></head>
  <body style="margin:0;padding:0;background-color:#f9fafb;font-family:Arial,Helvetica,sans-serif">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center" style="padding:40px 16px">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)">
          <tr><td style="padding:40px 40px 24px;text-align:center;border-bottom:1px solid #e5e7eb">
            {logo_html}
            <h1 style="margin:0;font-size:20px;color:#111827;font-weight:700">Восстановление пароля</h1>
          </td></tr>
          <tr><td style="padding:32px 40px;text-align:center">
            <p style="margin:0 0 24px;font-size:15px;color:#6b7280">Ваш код восстановления:</p>
            <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#111827;background:#f3f4f6;padding:20px;border-radius:12px;font-family:'Courier New',monospace">{code}</div>
            <p style="margin:24px 0 0;font-size:13px;color:#9ca3af">Код действителен <strong>15 минут</strong></p>
          </td></tr>
          <tr><td style="padding:24px 40px;text-align:center;background:#f9fafb;border-top:1px solid #e5e7eb;border-radius:0 0 16px 16px">
            <p style="margin:0;font-size:12px;color:#9ca3af">Это письмо отправлено автоматически. Если вы не запрашивали код, проигнорируйте это сообщение.</p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(user, password)
                server.sendmail(user, email, msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(user, email, msg.as_string())
        print(f"[EMAIL] Reset code sent to {email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send to {email}: {e}")
        return False
