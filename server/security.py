"""Creatier 프로덕션 설정."""

from __future__ import annotations

import os
import sys

DEMO_AUTH_SECRET = "creatier-local-dev-secret-32chars-minimum"


def is_production() -> bool:
    return os.environ.get("CREATIER_ENV", "").strip().lower() == "production"


def is_cloud_host() -> bool:
    return bool(os.environ.get("PORT", "").strip())


def apply_cloud_defaults() -> None:
    if not is_cloud_host():
        return
    if not os.environ.get("CREATIER_DATABASE", "").strip():
        os.environ["CREATIER_DATABASE"] = "/data/creatier.db"


def production_config_errors() -> list[str]:
    if not is_production():
        return []
    errors = []
    secret = os.environ.get("AUTH_SECRET", "").strip()
    if not secret or secret == DEMO_AUTH_SECRET or len(secret) < 32:
        errors.append("AUTH_SECRET: production에서 32자 이상 랜덤 값 필요")
    if not os.environ.get("CREATIER_ADMIN_EMAIL", "").strip():
        errors.append("CREATIER_ADMIN_EMAIL: 관리자 이메일 필요")
    if len(os.environ.get("CREATIER_ADMIN_PASSWORD", "")) < 8:
        errors.append("CREATIER_ADMIN_PASSWORD: 8자 이상 필요")
    url = os.environ.get("CREATIER_PUBLIC_URL", "").strip()
    if not url.startswith("https://"):
        errors.append("CREATIER_PUBLIC_URL: https:// 도메인 필요")
    if is_cloud_host() and not os.environ.get("CREATIER_DATABASE", "").startswith("/data/"):
        errors.append("CREATIER_DATABASE: Railway Volume /data/creatier.db 권장")
    if is_cloud_host() and os.environ.get("CREATIER_PORT", "").strip():
        errors.append("CREATIER_PORT: Railway에서는 설정하지 마세요 (PORT 자동 사용)")
    if is_cloud_host() and os.environ.get("CREATIER_OAUTH_DEV", "").lower() in ("1", "true", "yes"):
        errors.append("CREATIER_OAUTH_DEV: production에서 Mock OAuth 비활성화 필요")
    mail_ok = bool(os.environ.get("CREATIER_RESEND_API_KEY", "").strip()) or bool(
        os.environ.get("CREATIER_SMTP_HOST", "").strip()
    )
    if not mail_ok and os.environ.get("CREATIER_REQUIRE_MAIL", "").lower() == "true":
        errors.append("CREATIER_RESEND_API_KEY 또는 CREATIER_SMTP_*: 이메일 설정 필요")
    if os.environ.get("CREATIER_REQUIRE_OAUTH", "").lower() == "true":
        oauth_dev = os.environ.get("CREATIER_OAUTH_DEV", "").lower() in ("1", "true", "yes")
        if oauth_dev:
            errors.append("CREATIER_OAUTH_DEV: production에서 Mock OAuth 비활성화 필요")
        if not os.environ.get("META_APP_ID", "").strip() or not os.environ.get("META_APP_SECRET", "").strip():
            errors.append("META_APP_ID / META_APP_SECRET: Instagram OAuth 필요")
        if not os.environ.get("TIKTOK_CLIENT_KEY", "").strip() or not os.environ.get("TIKTOK_CLIENT_SECRET", "").strip():
            errors.append("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET: TikTok OAuth 필요")
    return errors


def exit_if_misconfigured() -> None:
    errors = production_config_errors()
    if errors:
        print("Creatier production config error:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
