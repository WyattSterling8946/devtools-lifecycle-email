import os

from src.email_lifecycle import InfraiEmail, LifecycleEvent, LifecycleMail, send_lifecycle_mail


recipient = os.environ.get("DEMO_EMAIL_TO")
if not recipient:
    raise SystemExit("DEMO_EMAIL_TO is required")

mail = LifecycleMail(LifecycleEvent.RELEASE, recipient, "shipping-api", "v2.4.0 is live")
print("message_id:", send_lifecycle_mail(mail, InfraiEmail()))
