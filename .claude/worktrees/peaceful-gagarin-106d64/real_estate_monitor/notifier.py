from __future__ import annotations
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import EvaluationResult


def send_email(result: EvaluationResult, cfg: dict) -> None:
    l = result.listing
    email_cfg = cfg["notification"]["email"]

    price_str = f"{l.price:,}".replace(",", " ") + " PLN" if l.price else "brak danych"
    ppm2_str = f"{l.price_per_m2:,}".replace(",", " ") + " PLN/m²" if l.price_per_m2 else "brak danych"
    area_str = f"{l.area} m²" if l.area else "brak danych"
    rooms_str = str(l.rooms) if l.rooms else "brak danych"

    subject = f"Nowa oferta: {l.title[:60]} — {price_str}"

    body = f"""
=== SZCZEGÓŁY OFERTY ===
Tytuł:       {l.title}
Cena:        {price_str}
Cena/m²:     {ppm2_str}
Metraż:      {area_str}
Pokoje:      {rooms_str}
Lokalizacja: {l.location or 'brak danych'}
Link:        {l.url}

=== OCENA AI ===
Dopasowanie: {'✅ MATCH' if result.is_match else '❌ NO MATCH'} ({result.score}/100)
Uzasadnienie: {result.reasoning}

Serwis: {l.source.upper()} | Znaleziono: {l.found_at.strftime('%Y-%m-%d %H:%M')}
    """.strip()

    msg = MIMEMultipart()
    msg["From"] = email_cfg["from"]
    msg["To"] = email_cfg["to"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    password = os.environ.get("EMAIL_PASSWORD", "")
    with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(email_cfg["from"], password)
        smtp.sendmail(email_cfg["from"], email_cfg["to"], msg.as_string())
