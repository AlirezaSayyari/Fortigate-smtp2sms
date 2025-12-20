# -*- coding: utf-8 -*-
import asyncio
import logging
from aiosmtpd.controller import Controller
import re
import requests
import json

# ==================== CONFIG ====================

# Allowed source (FortiGate) IP
ALLOWED_IP = "192.168.X.X"

# Primary SMS provider
PROV1_URL = "https://sms.provider1.com/api/Sms/Send"
PROV1_AUTH = "Basic XXXXXXXXXXXXXXXX="  # <-- replace with your real header value

# Secondary SMS provider
PROV2_URL = "https://console.provider2.com/api/send/shared/xxxxxxxxxxxxxxxxxx"
PROV2_BODY_ID = 1111111

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# =================================================


def extract_phone_and_code(envelope):
    """Extract phone number and OTP code from email."""
    phone = None
    for r in envelope.rcpt_tos:
        m = re.search(r"(09\d{9})", r)
        if m:
            phone = m.group(1)
            break

    body = envelope.content.decode(errors='ignore')
    m2 = re.search(r"code(?:\s*is)?\s*[:\-]?\s*(\d+)", body, re.IGNORECASE)
    code = m2.group(1) if m2 else None

    logging.info(f"Parsed phone={phone}, code={code}")
    return phone, code


def send_sms_provider1(mobile, token):
    """Send SMS via provider1."""
    payload = json.dumps({
        "MobileNo": mobile,
        "Content": f"Your Token code is {token}"
    })

    headers = {
        "Content-Type": "application/json",
        "Authorization": PROV1_AUTH,
        "cache-control": "no-cache"
    }

    try:
        resp = requests.post(PROV1_URL, headers=headers, data=payload, timeout=10)
        logging.info(f"[Provider1] HTTP {resp.status_code} - {resp.text.strip()}")
        if resp.status_code == 200 and re.match(r"^\d+$", resp.text.strip()):
            logging.info("[Provider1] SMS sent successfully.")
            return True
    except Exception as e:
        logging.error(f"[Provider1] Error: {e}")
    return False


def send_sms_provider2(mobile, token):
    """Send SMS via provider2."""
    payload = json.dumps({
        "bodyId": PROV2_BODY_ID,
        "to": mobile,
        "args": [token]
    })

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(PROV2_URL, headers=headers, data=payload, timeout=10)
        logging.info(f"[Provider2] HTTP {resp.status_code} - {resp.text.strip()}")

        if resp.status_code == 200:
            data = resp.json()
            if "recId" in data and str(data["recId"]).isdigit():
                logging.info("[Provider2] SMS sent successfully.")
                return True
    except Exception as e:
        logging.error(f"[Provider2] Error: {e}")
    return False


class SMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        peer_ip = session.peer[0]
        if peer_ip != ALLOWED_IP:
            logging.warning(f"Rejected unauthorized IP: {peer_ip}")
            return '550 Access denied'

        phone, code = extract_phone_and_code(envelope)
        if not phone or not code:
            logging.warning("Failed to parse phone or code")
            return '550 Failed to parse phone/code'

        logging.info(f"Sending SMS to {phone} with code {code}")

        # Try Provider1 first, fallback to Provider2
        if send_sms_provider1(phone, code):
            return '250 OK (Provider1)'
        elif send_sms_provider2(phone, code):
            return '250 OK (Provider2)'
        else:
            logging.error("All SMS providers failed.")
            return '451 Temporary failure'


def run_server(host="0.0.0.0", port=25):
    handler = SMTPHandler()
    controller = Controller(handler, hostname=host, port=port)
    controller.start()
    logging.info(f"SMTP→SMS Gateway started on {host}:{port} (Allowed IP: {ALLOWED_IP})")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()


if __name__ == "__main__":
    run_server()
