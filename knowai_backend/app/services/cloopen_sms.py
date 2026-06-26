"""容联云通讯短信发送服务（基于官方 SDK）。"""
import asyncio

from ronglian_sms_sdk import SmsSDK

from app.config import settings


class CloopenSmsClient:
    def __init__(self, account_sid: str, auth_token: str, app_id: str, template_id: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.app_id = app_id
        self.template_id = template_id
        self._sdk = SmsSDK(account_sid, auth_token, app_id)

    @property
    def enabled(self) -> bool:
        """所有配置项（含 template_id）就绪后才启用真实发送。"""
        return bool(self.account_sid and self.auth_token and self.app_id and self.template_id)

    async def send(self, to: str, datas: tuple[str, ...]) -> dict:
        """发送短信。

        Args:
            to: 接收手机号（中国大陆 11 位即可）。
            datas: 模板变量元组，如 ("123456", "5")。

        Returns:
            SDK 响应字典，如 {"statusCode": "000000", ...}。
        """
        if not self.enabled:
            raise RuntimeError("Cloopen SMS not configured (missing template_id)")
        # SDK 的 sendMessage 是同步方法，使用 to_thread 避免阻塞事件循环
        return await asyncio.to_thread(self._sdk.sendMessage, self.template_id, to, datas)


_sms_client: CloopenSmsClient | None = None


def get_sms_client() -> CloopenSmsClient | None:
    global _sms_client
    if _sms_client is None and settings.cloopen_account_sid:
        _sms_client = CloopenSmsClient(
            account_sid=settings.cloopen_account_sid,
            auth_token=settings.cloopen_auth_token,
            app_id=settings.cloopen_app_id,
            template_id=settings.cloopen_template_id,
        )
    return _sms_client
