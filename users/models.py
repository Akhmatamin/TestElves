from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from datetime import timedelta


class UserProfile(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin"
        CLIENT = "client"
        WORKER = "worker"

    phone_number = PhoneNumberField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CLIENT)
    otchestvo = models.CharField(max_length=20)
    address = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.first_name} ({self.phone_number})"

    def full_name(self):
        return f'{self.first_name} {self.last_name} {self.otchestvo}'

class PhoneNumberCheck(models.Model):
    phone = PhoneNumberField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > (self.created_at + timedelta(minutes=2))

    def __str__(self):
        return f"SMS to {self.phone}"


class KYCVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="kyc")

    passport_photo_front = models.ImageField(upload_to="kyc/passport/")
    passport_photo_back = models.ImageField(upload_to="kyc/passport/")
    selfie_photo = models.ImageField(upload_to="kyc/selfie/")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reject_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"KYC for {self.user.phone_number} — {self.status}"

