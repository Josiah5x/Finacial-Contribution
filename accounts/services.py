
import secrets
import hashlib
import hmac

from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import EmailOTP


OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 60
OTP_DAILY_LIMIT = 5


def generate_email_otp(email):
    email = email.strip().lower()
    now = timezone.now()

    # Prevent frequent resend requests.
    recent_otp = EmailOTP.objects.filter(
        email=email,
        created_at__gte=now - timedelta(seconds=OTP_RESEND_SECONDS)
    ).exists()

    if recent_otp:
        raise ValidationError(
            'Please wait 60 seconds before requesting another code.'
        )

    # Limit OTP requests per day.
    daily_count = EmailOTP.objects.filter(
        email=email,
        created_at__date=timezone.localdate()
    ).count()

    if daily_count >= OTP_DAILY_LIMIT:
        raise ValidationError(
            'You have reached the daily verification code limit.'
        )

    # Generate secure six-digit OTP.
    otp = f'{secrets.randbelow(1000000):06d}'
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()

    # Save OTP temporarily.
    otp_record = EmailOTP.objects.create(
        email=email,
        otp_hash=otp_hash,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    )

    try:
        subject = 'Verify your email address | DailyCollect'

        plain_message = f"""
        Hello,

        Welcome to DailyCollect!

        Your email verification code is:

        {otp}

        This code expires in 10 minutes.

        For your security, never share this code with anyone.

        If you did not request this verification, you can safely ignore this email.

        The DailyCollect Team
        """


        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DailyCollect Verification Code</title>
        </head>

        <body style="margin:0; padding:25px 15px;
                    background:#ffffff;
                    font-family:Arial,Helvetica,sans-serif;">

        <table width="100%" cellpadding="0" cellspacing="0"
            style="max-width:650px; margin:auto;">

            <tr>
                <td style="padding:5px 0 25px;">
                    <span style="font-size:25px; font-weight:bold;
                                color:#08264b;">
                        Daily<span style="color:#12b76a;">Collect</span>
                    </span>
                </td>
            </tr>

            <tr>
                <td style="background:#eef3fa;
                        border-radius:12px;
                        padding:20px 17px;">

                    <p style="font-size:14px;
                            color:#424b57;
                            margin:0 0 15px;">
                        Code Requested
                    </p>

                    <!-- Six separate OTP digits -->
                    <table cellpadding="0" cellspacing="4">
                        <tr>
                            {''.join(
                                f'<td style="background:#ffffff; border-radius:4px; '
                                f'width:28px; height:36px; text-align:center; '
                                f'vertical-align:middle; font-size:24px; '
                                f'color:#172033; font-weight:500;">{digit}</td>'
                                for digit in otp
                            )}
                        </tr>
                    </table>

                    <!-- Action-style button -->
                    <table cellpadding="0" cellspacing="0"
                        style="margin-top:20px;">
                        <tr>
                            <td style="background:#006da8;
                                    border-radius:25px;
                                    padding:12px 25px;
                                    color:#ffffff;
                                    font-size:14px;
                                    font-weight:bold;">
                                Your verification code
                            </td>
                        </tr>
                    </table>

                    <p style="font-size:13px;
                            color:#64748b;
                            margin:17px 0 0;">
                        This code expires in <strong>10 minutes</strong>.
                    </p>

                </td>
            </tr>

            <tr>
                <td style="padding:25px 5px;">

                    <p style="font-size:13px;
                            line-height:1.7;
                            color:#475569;">
                        You requested an email verification code for your
                        DailyCollect account.
                    </p>

                    <p style="font-size:13px;
                            line-height:1.7;
                            color:#475569;">
                        For your security, never share this code with anyone.
                        DailyCollect will never ask you to disclose your OTP.
                    </p>

                    <p style="font-size:13px;
                            color:#64748b;
                            margin-top:25px;">
                        If you did not request this code, you can safely
                        ignore this email.
                    </p>

                    <p style="font-size:13px; color:#08264b;">
                        Regards,<br>
                        <strong>DailyCollect Security Team</strong>
                    </p>

                </td>
            </tr>

            <tr>
                <td style="border-top:1px solid #e5e7eb;
                        padding-top:18px;
                        text-align:center;">

                    <p style="font-size:11px; color:#94a3b8;">
                        © DailyCollect. All rights reserved.
                    </p>

                    <p style="font-size:11px; color:#94a3b8;">
                        Smart management of daily contributions.
                    </p>

                </td>
            </tr>

        </table>
        </body>
        </html>
        """


    # Build and send HTML email.
    email_message = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.attach_alternative(
        html_message,
        "text/html"
    )

    # DEBUG: Inspect the actual OTP email before sending.
    mime_message = email_message.message()

    print("EMAIL CONTENT TYPE:", mime_message.get_content_type())

    for part in mime_message.walk():
        print("EMAIL PART:", part.get_content_type())

        if part.get_content_type() == "text/html":
            print("HTML CONTENT:")
            print(part.get_payload(decode=True).decode(
                part.get_content_charset() or "utf-8"
            ))

    email_message.send(fail_silently=False)

    except Exception:
        otp_record.delete()
        raise

    # Invalidate previous OTPs after successful email delivery.
    EmailOTP.objects.filter(
        email=email,
        is_used=False
    ).exclude(
        pk=otp_record.pk
    ).update(is_used=True)

    return True


def verify_email_otp(email, otp):
    email = email.strip().lower()
    otp = otp.strip()

    if not otp.isdigit() or len(otp) != 6:
        return False

    otp_record = EmailOTP.objects.filter(
        email=email,
        is_used=False
    ).order_by('-created_at').first()

    if not otp_record:
        return False

    if otp_record.is_expired():
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])
        return False

    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])
        return False

    # Count every verification attempt.
    otp_record.attempts += 1

    submitted_hash = hashlib.sha256(otp.encode()).hexdigest()

    if not hmac.compare_digest(
        otp_record.otp_hash,
        submitted_hash
    ):
        if otp_record.attempts >= OTP_MAX_ATTEMPTS:
            otp_record.is_used = True

        otp_record.save(update_fields=['attempts', 'is_used'])
        return False

    # OTP successfully verified.
    otp_record.is_used = True
    otp_record.verified_at = timezone.now()

    otp_record.save(
        update_fields=['attempts', 'is_used', 'verified_at']
    )

    return True
