"""Envío de alertas por email. Todo con `smtplib` de la librería estándar —
sin dependencias nuevas.
"""

from __future__ import annotations

import html
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config


def _recipients() -> list[str]:
    return [addr.strip() for addr in config.EMAIL_TO.split(",") if addr.strip()]


def _connect() -> smtplib.SMTP:
    if not (config.SMTP_USER and config.SMTP_PASSWORD and config.EMAIL_TO):
        raise RuntimeError(
            "Falta configurar SMTP_USER, SMTP_PASSWORD o EMAIL_TO. Mirá .env.example."
        )
    server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
    server.starttls()
    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
    return server


def send_alert(subject: str, body: str, chart_png: bytes | None = None) -> None:
    """Manda el mail de alerta. Si hay gráfico, va adjunto e incrustado en el
    cuerpo HTML; si no, el mail es texto plano nomás."""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = ", ".join(_recipients())

    if chart_png:
        alt = MIMEMultipart("alternative")
        msg.attach(alt)
        alt.attach(MIMEText(body, "plain"))
        # El título/URL del producto viajan sin sanitizar hasta acá — al
        # texto plano no le importa, pero insertado crudo en HTML un
        # "<" en un título rompería el render. Escapamos solo esta copia.
        html_body = html.escape(body).replace("\n", "<br>") + '<br><br><img src="cid:chart">'
        alt.attach(MIMEText(html_body, "html"))

        image = MIMEImage(chart_png)
        image.add_header("Content-ID", "<chart>")
        image.add_header("Content-Disposition", "inline", filename="precio.png")
        msg.attach(image)
    else:
        msg.attach(MIMEText(body, "plain"))

    with _connect() as server:
        server.sendmail(config.EMAIL_FROM, _recipients(), msg.as_string())


def send_test_email() -> None:
    send_alert(
        subject="✅ price-watcher: setup verificado",
        body="Si estás leyendo esto, el envío de mails está bien configurado.",
    )
