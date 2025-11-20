from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from broker.models import BalanceAccount

@receiver(post_save, sender=UserProfile)
def create_balance_account(sender, instance, created, **kwargs):
    if created:
        BalanceAccount.objects.create(user=instance)
