import asyncio
import base64
import http.client
import io
import json
import logging
import uuid
from decimal import Decimal
from urllib.parse import urlencode, urlparse

import qrcode
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient, THREAD_LOCAL
from alipay.aop.api.domain.AlipayTradePrecreateModel import AlipayTradePrecreateModel
from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
from alipay.aop.api.request.AlipayTradePrecreateRequest import AlipayTradePrecreateRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.util.SignatureUtils import verify_with_rsa
from cryptography.hazmat.primitives import serialization

from app.config import settings

logger = logging.getLogger(__name__)

_client: DefaultAlipayClient | None = None


def _to_pkcs1_private_key(key_str: str) -> str:
    """Convert any private key (PKCS#8, raw base64, etc.) to PKCS#1 PEM format."""
    raw = key_str.strip()
    try:
        if raw.startswith("-----"):
            private_key = serialization.load_pem_private_key(raw.encode(), password=None)
        else:
            der = base64.b64decode(raw)
            private_key = serialization.load_der_private_key(der, password=None)
    except Exception:
        pem = "-----BEGIN PRIVATE KEY-----\n" + raw + "\n-----END PRIVATE KEY-----"
        private_key = serialization.load_pem_private_key(pem.encode(), password=None)
    pkcs1 = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pkcs1.decode()


def _to_spki_public_key(key_str: str) -> str:
    """Convert any public key format to X.509 SPKI PEM (for SDK verify)."""
    raw = key_str.strip()
    try:
        if raw.startswith("-----"):
            public_key = serialization.load_pem_public_key(raw.encode())
        else:
            padding = 4 - len(raw) % 4
            if padding != 4:
                raw += "=" * padding
            der = base64.b64decode(raw)
            public_key = serialization.load_der_public_key(der)
    except Exception:
        pem = "-----BEGIN PUBLIC KEY-----\n" + raw + "\n-----END PUBLIC KEY-----"
        public_key = serialization.load_pem_public_key(pem.encode())
    spki = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return spki.decode()


def _get_alipay_client() -> DefaultAlipayClient:
    global _client
    if _client is not None:
        return _client
    config = AlipayClientConfig()
    config.app_id = settings.alipay_appid
    config.app_private_key = _to_pkcs1_private_key(settings.alipay_private_key)
    config.alipay_public_key = _to_spki_public_key(settings.alipay_public_key)
    config.sign_type = "RSA2"
    if settings.alipay_sandbox:
        config.server_url = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
    _client = DefaultAlipayClient(alipay_client_config=config, logger=logger)
    return _client


def _generate_qr_data_url(content: str) -> str:
    """Generate a QR code image and return as base64 data URL."""
    img = qrcode.make(content)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


async def create_alipay_order(order_sn: str, amount: Decimal) -> dict[str, str | bool]:
    """Create an Alipay Precreate order and return QR code data URL."""
    model = AlipayTradePrecreateModel()
    model.out_trade_no = order_sn
    model.total_amount = float(amount)
    model.subject = "学伴 - 课程购买"

    request = AlipayTradePrecreateRequest(biz_model=model)
    request.notify_url = f"{settings.notify_url}"

    client = _get_alipay_client()
    loop = asyncio.get_running_loop()

    for attempt in range(3):
        try:
            raw = await loop.run_in_executor(None, _signed_request, client, request, attempt)
            if raw is None:
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                logger.error("Alipay create order failed after 3 retries")
                return {"pay_url": "", "qr_code_url": "", "form": "", "mock": False}

            data = json.loads(raw)
            resp = data.get("alipay_trade_precreate_response", data)
            if resp.get("code") != "10000":
                logger.warning(f"Alipay error: {resp}")
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return {"pay_url": "", "qr_code_url": "", "form": "", "mock": False}

            qr_code_str = resp.get("qr_code", "")
            if not qr_code_str:
                logger.error(f"Alipay precreate missing qr_code: {resp}")
                return {"pay_url": "", "qr_code_url": "", "form": "", "mock": False}

            qr_code_url = _generate_qr_data_url(qr_code_str)
            return {"pay_url": "", "qr_code_url": qr_code_url, "form": "", "mock": False}

        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            logger.error(f"Alipay create order failed: {e}", exc_info=True)
            return {"pay_url": "", "qr_code_url": "", "form": "", "mock": False}

    return {"pay_url": "", "qr_code_url": "", "form": "", "mock": False}


def _signed_request(client: DefaultAlipayClient, request, attempt: int) -> str | None:
    """Execute a signed API call, returning the raw JSON response string."""
    try:
        THREAD_LOCAL.uuid = str(uuid.uuid1())
        THREAD_LOCAL.logger = logger

        # Use SDK to prepare signed params
        prepare = client._DefaultAlipayClient__prepare_request
        config = client._DefaultAlipayClient__config
        query_string, params = prepare(request)

        url = config.server_url + "?" + query_string
        body = urlencode(params).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }

        host = urlparse(url).hostname
        path = urlparse(url).path + "?" + query_string
        conn = http.client.HTTPSConnection(host, timeout=15)
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        result = resp.read().decode("utf-8")
        conn.close()
        return result
    except Exception as e:
        logger.warning(f"Alipay API call failed (attempt {attempt + 1}): {e}")
        return None


def query_alipay_trade(order_sn: str) -> str | None:
    """Query Alipay trade status. Returns 'TRADE_SUCCESS', 'WAIT_BUYER_PAY', or None on failure."""
    try:
        model = AlipayTradeQueryModel()
        model.out_trade_no = order_sn

        request = AlipayTradeQueryRequest(biz_model=model)
        client = _get_alipay_client()

        THREAD_LOCAL.uuid = str(uuid.uuid1())
        THREAD_LOCAL.logger = logger
        prepare = client._DefaultAlipayClient__prepare_request
        config = client._DefaultAlipayClient__config
        query_string, params = prepare(request)

        body = urlencode(params).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
        host = urlparse(config.server_url).hostname
        conn = http.client.HTTPSConnection(host, timeout=10)
        conn.request("POST", "/gateway.do?" + query_string, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        conn.close()

        data = json.loads(raw)
        query_resp = data.get("alipay_trade_query_response", data)
        if query_resp.get("code") == "10000":
            return query_resp.get("trade_status")
        logger.warning(f"Alipay trade query failed: {query_resp}")
        return None
    except Exception as e:
        logger.warning(f"Alipay trade query error: {e}")
        return None


def verify_alipay_notify(payload: dict) -> bool:
    """Verify Alipay async notification signature."""
    try:
        params = payload.copy()
        sign = params.pop("sign", "")
        sign_type = params.pop("sign_type", "RSA2")

        sorted_keys = sorted(params.keys())
        content = "&".join(f"{k}={params[k]}" for k in sorted_keys)

        return verify_with_rsa(
            content=content,
            sign=sign,
            alipay_public_key=_to_spki_public_key(settings.alipay_public_key),
            sign_type=sign_type,
        )
    except Exception as e:
        logger.error(f"Alipay notify verify failed: {e}", exc_info=True)
        return False
