from decimal import Decimal

MOCK_QR_CODE_URL = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=mockpay"


async def create_wechat_order(order_sn: str, amount: Decimal) -> dict[str, str | bool]:
    return {"pay_url": MOCK_QR_CODE_URL, "qr_code_url": MOCK_QR_CODE_URL, "mock": True}


def verify_wechat_notify(payload: dict) -> bool:
    return True
