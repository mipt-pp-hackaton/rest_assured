"""Email sender module using aiosmtplib + Jinja2."""

from email.message import EmailMessage
from typing import Tuple

from aiosmtplib import SMTP
from jinja2 import Environment, PackageLoader, select_autoescape
from loguru import logger

from rest_assured.src.configs.app.smtp import SmtpConfig

_env = Environment(
    loader=PackageLoader("rest_assured.src.services.notifications", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
)


def _render(template_name: str, context: dict) -> str:
    template = _env.get_template(template_name)
    return template.render(context)


class EmailSender:
    def __init__(self, smtp_config: SmtpConfig) -> None:
        self._cfg = smtp_config

    async def send(
        self,
        *,
        to: list[str],
        kind: str,
        context: dict,
    ) -> Tuple[bool, str | None]:
        """Send a multipart/alternative email using Jinja2 templates.

        Returns (True, None) on success, or (False, error_message) on failure.
        Never raises exceptions.
        """
        recipients = [addr.strip() for addr in (to or []) if addr and addr.strip()]
        if not recipients:
            # Слать письмо некому (у сервиса не задан owner_emails) — это не сбой
            # SMTP, а отсутствие конфигурации получателей. Не пытаемся отправлять,
            # не шумим ERROR'ом; фиксируем причину для notification_log.
            logger.warning(f"Skipping email (kind={kind}): no recipients configured")
            return False, "no recipients configured"
        try:
            subject = _render(f"{kind}.subject.j2", context).strip()
            text_body = _render(f"{kind}.txt.j2", context)
            html_body = _render(f"{kind}.html.j2", context)

            msg = EmailMessage()
            msg["From"] = f"{self._cfg.from_name} <{self._cfg.from_email}>"
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.set_content(text_body)
            msg.add_alternative(html_body, subtype="html")

            smtp_kwargs: dict = {
                "hostname": self._cfg.host,
                "port": self._cfg.port,
                "use_tls": self._cfg.use_tls,
                "validate_certs": self._cfg.validate_certs,
                "timeout": self._cfg.timeout_seconds,
            }
            # start_tls передаём только при отсутствии implicit TLS — aiosmtplib
            # запрещает одновременно use_tls=True и start_tls=True. None оставляем
            # на усмотрение библиотеки (оппортунистический STARTTLS).
            if not self._cfg.use_tls and self._cfg.start_tls is not None:
                smtp_kwargs["start_tls"] = self._cfg.start_tls

            async with SMTP(**smtp_kwargs) as smtp:
                if self._cfg.user:
                    await smtp.login(self._cfg.user, self._cfg.password.get_secret_value())
                await smtp.send_message(msg)

            logger.info(f"Email sent: kind={kind}, to={to}")
            return True, None
        except Exception as e:
            logger.error(f"Failed to send email (kind={kind}): {e}")
            return False, f"{type(e).__name__}: {e}"
