from django.db import models
from django.utils import timezone
from users.models import UserProfile


# BALANCE

class BalanceAccount(models.Model):
    user = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="balance"
    )
    amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    def __str__(self):
        return f"{self.user.phone_number} — {self.amount}"


class BalanceTransaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit"
        WITHDRAW = "withdraw"
        CORRECTION = "correction"

    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.phone_number} | {self.type} | {self.amount}"



# STOCKS


class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=150)

    # Твои важные поля (НЕ УБИРАЕМ)
    series_number = models.IntegerField(null=True, blank=True)
    gos_number = models.CharField(max_length=20, unique=True)
    nominal_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    previous_close = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    industry = models.CharField(max_length=64, null=True, blank=True)

    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="stock_images/", null=True, blank=True)

    current_price = models.DecimalField(max_digits=18, decimal_places=4)
    available_quantity = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticker}"


# NEWS

class News(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    image = models.ImageField(upload_to="news/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# ORDERS

class Order(models.Model):
    class Type(models.TextChoices):
        BUY = "buy"
        SELL = "sell"

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        CANCELLED = "cancelled"

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)

    type = models.CharField(max_length=20, choices=Type.choices)  # buy/sell
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=4)
    total = models.DecimalField(max_digits=18, decimal_places=4)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order {self.id}: {self.user.phone_number} {self.type}"



# PORTFOLIO

class PortfolioItem(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=0)
    average_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)


    def __str__(self):
        return f"{self.user.phone_number}: {self.quantity} × {self.stock.ticker}"
