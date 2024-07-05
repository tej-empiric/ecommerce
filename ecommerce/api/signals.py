from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import *


@receiver(post_save, sender=CustomUser)
def create_referral_code(sender, instance, created, **kwargs):
    if created:
        ReferralCode.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
