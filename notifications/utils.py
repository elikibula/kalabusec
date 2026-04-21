from .models import Notification


def create_notification(recipient, message, notif_type='general', link=''):
    Notification.objects.create(
        recipient=recipient,
        message=message,
        notif_type=notif_type,
        link=link or ''
    )