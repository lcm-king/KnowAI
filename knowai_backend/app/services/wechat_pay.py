from decimal import Decimal

MOCK_QR_CODE_URL = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=mockpay"


async def create_wechat_order(order_sn: str, amount: Decimal) -> dict[str, str | bool]:
    # 微信 Native 支付尚未接入真实 SDK,仅返回 mock 二维码。
    # 真实支付请通过 simulate_pay_success(开发)或接入微信 SDK 后新增 /notify/wechat 验签回调。
    return {"pay_url": MOCK_QR_CODE_URL, "qr_code_url": MOCK_QR_CODE_URL, "mock": True}


def verify_wechat_notify(payload: dict) -> bool:
    # 未接入真实微信支付 SDK,无法验签。
    # 拒绝一切外部 wechat 回调,防止伪造订单状态。
    # mock 微信支付通过 simulate_pay_success 内部完成,不经过此回调。
    return False
