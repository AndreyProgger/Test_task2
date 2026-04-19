from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
import logging

from accounts.models import User, Profile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Автоматически создаёт Profile при создании нового User.
    """
    if created:
        Profile.objects.create(user=instance)
        logger.info(f'Создан профиль для пользователя: {instance.email}')


@receiver(pre_delete, sender=User)
def delete_user_profile(sender, instance, **kwargs):
    """
    При удалении пользователя удаляет аватар из файловой системы.
    Сам Profile удалится каскадно (CASCADE).
    """
    try:
        profile = instance.profile
        if profile.avatar:
            if default_storage.exists(profile.avatar.name):
                default_storage.delete(profile.avatar.name)
                logger.info(f'Удалён аватар пользователя {instance.email}')
    except Profile.DoesNotExist:
        pass

    logger.info(f'Пользователь {instance.email} удалён, профиль будет удалён каскадно')