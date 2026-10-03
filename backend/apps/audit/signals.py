from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from .services import record


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    record("auth.login", actor=user, request=request, subject_user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    # Only the email domain: enough to spot attacks, no account enumeration trail.
    email = str((credentials or {}).get("email") or (credentials or {}).get("username") or "")
    record("auth.login_failed", request=request, actor_type="visitor", email_domain=email.rsplit("@", 1)[-1][:100] if "@" in email else None)
