"""Email sending via Resend — verification and password reset."""

from __future__ import annotations

import logging

import resend

from app.config import settings

logger = logging.getLogger(__name__)

# From address — Resend free tier requires onboarding@resend.dev
FROM_ADDRESS = "Wadjet <onboarding@resend.dev>"


def _send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured — email not sent to %s", to)
        return False

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_verification_email(to: str, token: str) -> bool:
    """Send email verification link."""
    verify_url = f"{settings.base_url}/api/auth/verify-email?token={token}"
    html = f"""
    <div style="font-family: Inter, sans-serif; max-width: 480px; margin: 0 auto; background: #0A0A0A; border: 1px solid #2a2a2a; border-radius: 12px; padding: 32px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px;">𓂀</span>
            <h1 style="color: #D4AF37; font-size: 20px; margin: 8px 0 0;">Verify your email</h1>
        </div>
        <p style="color: #F5F0E8; font-size: 14px; line-height: 1.6;">
            Welcome to Wadjet! Click the button below to verify your email address.
        </p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="{verify_url}" style="display: inline-block; background: #D4AF37; color: #0A0A0A; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Verify Email
            </a>
        </div>
        <p style="color: #8B7355; font-size: 12px; line-height: 1.5;">
            This link expires in 24 hours. If you didn't create a Wadjet account, you can safely ignore this email.
        </p>
    </div>
    """
    return _send_email(to, "Verify your Wadjet email", html)


def send_password_reset_email(to: str, token: str) -> bool:
    """Send password reset link."""
    reset_url = f"{settings.base_url}/api/auth/reset-password?token={token}"
    html = f"""
    <div style="font-family: Inter, sans-serif; max-width: 480px; margin: 0 auto; background: #0A0A0A; border: 1px solid #2a2a2a; border-radius: 12px; padding: 32px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px;">𓂀</span>
            <h1 style="color: #D4AF37; font-size: 20px; margin: 8px 0 0;">Reset your password</h1>
        </div>
        <p style="color: #F5F0E8; font-size: 14px; line-height: 1.6;">
            We received a request to reset your Wadjet password. Click the button below to choose a new one.
        </p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="{reset_url}" style="display: inline-block; background: #D4AF37; color: #0A0A0A; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Reset Password
            </a>
        </div>
        <p style="color: #8B7355; font-size: 12px; line-height: 1.5;">
            This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
        </p>
    </div>
    """
    return _send_email(to, "Reset your Wadjet password", html)
