# -*- coding: utf-8 -*-
import asyncio
import logging
from aiosmtpd.controller import Controller
import re
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== CONFIG ====================

def load_config():
    """Load configuration from environment variables."""
    global ALLOWED_IP, PROVIDERS, PRIORITY_ORDER
    ALLOWED_IP = os.getenv("ALLOWED_IP")

    PROVIDERS = {}
    for i in range(1, 4):  # Assuming up to 3 providers
        name = os.getenv(f"PROVIDER{i}_NAME")
        if name:
            PROVIDERS[name] = {
                "url": os.getenv(f"PROVIDER{i}_URL"),
                "auth": os.getenv(f"PROVIDER{i}_AUTH"),
                "body_id": os.getenv(f"PROVIDER{i}_BODY_ID"),
                "srcnum": os.getenv(f"PROVIDER{i}_SRCNUM"),
            }

    PRIORITY_ORDER = [p.strip() for p in os.getenv("PROVIDER_PRIORITY", "provider1,provider2,provider3").split(",")]

# Initial load
load_config()

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


def send_sms_provider1(mobile, token, config):
    """Send SMS via provider1."""
    payload = json.dumps({
        "MobileNo": mobile,
        "Content": f"Your Token code is {token}"
    })

    headers = {
        "Content-Type": "application/json",
        "Authorization": config.get("auth"),
        "cache-control": "no-cache"
    }

    try:
        resp = requests.post(config["url"], headers=headers, data=payload, timeout=10)
        logging.info(f"[Provider1] HTTP {resp.status_code} - {resp.text.strip()}")
        if resp.status_code == 200 and re.match(r"^\d+$", resp.text.strip()):
            logging.info("[Provider1] SMS sent successfully.")
            return True
    except Exception as e:
        logging.error(f"[Provider1] Error: {e}")
    return False


def send_sms_provider2(mobile, token, config):
    """Send SMS via provider2."""
    payload = json.dumps({
        "bodyId": config.get("body_id"),
        "to": mobile,
        "args": [token]
    })

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(config["url"], headers=headers, data=payload, timeout=20)
        logging.info(f"[Provider2] HTTP {resp.status_code} - {resp.text.strip()}")

        if resp.status_code == 200:
            data = resp.json()
            if "recId" in data and str(data["recId"]).isdigit():
                logging.info("[Provider2] SMS sent successfully.")
                return True
    except Exception as e:
        logging.error(f"[Provider2] Error: {e}")
    return False

def send_sms_provider3(mobile, token, config):
    """Send SMS via provider3."""
    payload = json.dumps([{
        "srcNum": config.get("srcnum"),
        "recipient": mobile,
        "body": f"Your Token code is {token}"
    }])

    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.get("auth")
    }

    try:
        resp = requests.post(config["url"], headers=headers, data=payload, timeout=10)
        logging.info(f"[Provider3] HTTP {resp.status_code} - {resp.text.strip()}")

        if resp.status_code == 200:
            data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
            if item.get("statusCode") == 200 and item.get("messageId", 0) > 0:
                logging.info("[Provider3] SMS sent successfully.")
                return True
    except Exception as e:
        logging.error(f"[Provider3] Error: {e}")
    return False


def send_sms(mobile, token, provider_name):
    """Send SMS via the specified provider."""
    if provider_name not in PROVIDERS:
        logging.error(f"Provider {provider_name} not configured.")
        return False

    config = PROVIDERS[provider_name]
    if provider_name == "provider1":
        return send_sms_provider1(mobile, token, config)
    elif provider_name == "provider2":
        return send_sms_provider2(mobile, token, config)
    elif provider_name == "provider3":
        return send_sms_provider3(mobile, token, config)
    else:
        logging.error(f"Unknown provider: {provider_name}")
        return False


class SMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        # Reload config on each request to allow runtime changes
        load_dotenv(override=True)
        load_config()

        peer_ip = session.peer[0]
        if peer_ip != ALLOWED_IP:
            logging.warning(f"Rejected unauthorized IP: {peer_ip}")
            return '550 Access denied'

        phone, code = extract_phone_and_code(envelope)
        if not phone or not code:
            logging.warning("Failed to parse phone or code")
            return '550 Failed to parse phone/code'

        logging.info(f"Sending SMS to {phone} with code {code}")

        # Try providers in priority order
        for provider in PRIORITY_ORDER:
            if send_sms(phone, code, provider):
                return f'250 OK ({provider})'

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
