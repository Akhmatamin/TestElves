from rest_framework import serializers
from django.utils import timezone

from .models import (
    BalanceAccount,
    BalanceTransaction,
    Stock,
    Order,
    PortfolioItem,
    News,
)


# -------------------------------------
# BALANCE
# -------------------------------------

class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceAccount
        fields = ["amount"]


class BalanceTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceTransaction
        fields = ["id", "type", "amount", "comment", "created_at"]


# -------------------------------------
# STOCKS
# -------------------------------------

class StockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = [
            "id",
            "ticker",
            "name",
            "current_price",
            "image",
            "gos_number",
        ]


class StockDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = "__all__"


# -------------------------------------
# ORDERS
# -------------------------------------

class CreateOrderSerializer(serializers.Serializer):
    stock_id = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate(self, data):
        user = self.context["request"].user

        # кол-во
        if data["quantity"] <= 0:
            raise serializers.ValidationError("Количество должно быть > 0")

        # акция
        try:
            stock = Stock.objects.get(id=data["stock_id"])
        except Stock.DoesNotExist:
            raise serializers.ValidationError("Акция не найдена")

        data["stock"] = stock

        # цена
        total = stock.current_price * data["quantity"]

        # баланс
        if user.balance.amount < total:
            raise serializers.ValidationError("Недостаточно средств")

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        stock = validated_data["stock"]
        quantity = validated_data["quantity"]

        total = stock.current_price * quantity

        order = Order.objects.create(
            user=user,
            stock=stock,
            quantity=quantity,
            price=stock.current_price,
            total=total,
            type=Order.Type.BUY,
            status=Order.Status.PENDING,
        )

        return order


class OrderListSerializer(serializers.ModelSerializer):
    stock_ticker = serializers.CharField(source="stock.ticker")
    stock_name = serializers.CharField(source="stock.name")

    class Meta:
        model = Order
        fields = [
            "id",
            "type",
            "status",
            "stock_ticker",
            "stock_name",
            "quantity",
            "price",
            "total",
            "created_at",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    stock_ticker = serializers.CharField(source="stock.ticker")
    stock_name = serializers.CharField(source="stock.name")

    class Meta:
        model = Order
        fields = [
            "id",
            "type",
            "status",
            "stock_ticker",
            "stock_name",
            "quantity",
            "price",
            "total",
            "created_at",
            "processed_at",
        ]


class CancelOrderSerializer(serializers.Serializer):
    def validate(self, data):
        order = self.context["order"]
        user = self.context["user"]

        if order.user != user:
            raise serializers.ValidationError("Вы не можете отменить этот ордер")

        if order.status != Order.Status.PENDING:
            raise serializers.ValidationError("Можно отменить только PENDING ордер")

        return data

    def save(self):
        order = self.context["order"]
        order.status = Order.Status.CANCELLED
        order.save()
        return order



# -------------------------------------
# PROCESS ORDER (admin/worker)
# -------------------------------------

class ProcessOrderSerializer(serializers.Serializer):
    approve = serializers.BooleanField()

    def validate(self, data):
        order = self.context["order"]

        if order.status != Order.Status.PENDING:
            raise serializers.ValidationError("Этот ордер уже обработан")

        return data

    def save(self):
        order = self.context["order"]
        user = order.user
        stock = order.stock
        quantity = order.quantity
        total = order.total
        approve = self.validated_data["approve"]

        # 1. Отклонение
        if not approve:
            order.status = Order.Status.REJECTED
            order.processed_at = timezone.now()
            order.save()
            return order

        # 2. BUY логика
        if order.type == Order.Type.BUY:

            if user.balance.amount < total:
                raise serializers.ValidationError("Недостаточно средств")

            if stock.available_quantity < quantity:
                raise serializers.ValidationError("Недостаточно акций")

            # списываем деньги
            user.balance.amount -= total
            user.balance.save()

            BalanceTransaction.objects.create(
                user=user,
                type=BalanceTransaction.Type.WITHDRAW,
                amount=total,
                comment=f"Покупка {stock.ticker}",
            )

            # обновляем портфель
            item, created = PortfolioItem.objects.get_or_create(
                user=user, stock=stock
            )

            if created or item.quantity == 0:
                item.average_price = order.price
            else:
                old_total = item.average_price * item.quantity
                new_total = old_total + total
                item.average_price = new_total / (item.quantity + quantity)

            item.quantity += quantity
            item.save()

            # обновление количества акций
            stock.available_quantity -= quantity
            stock.save()

        # 3. SELL логика
        if order.type == Order.Type.SELL:

            item = PortfolioItem.objects.get(user=user, stock=stock)

            if item.quantity < quantity:
                raise serializers.ValidationError("Недостаточно акций для продажи")

            # уменьшаем портфель
            item.quantity -= quantity
            item.save()

            # возвращаем акции компании
            stock.available_quantity += quantity
            stock.save()

            # начисляем деньги
            user.balance.amount += total
            user.balance.save()

            BalanceTransaction.objects.create(
                user=user,
                type=BalanceTransaction.Type.DEPOSIT,
                amount=total,
                comment=f"Продажа {stock.ticker}",
            )

        # 4. финализация
        order.status = Order.Status.APPROVED
        order.processed_at = timezone.now()
        order.save()

        return order


# -------------------------------------
# SELL ORDER (client)
# -------------------------------------

class CreateSellOrderSerializer(serializers.Serializer):
    stock_id = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate(self, data):
        user = self.context["request"].user

        if data["quantity"] <= 0:
            raise serializers.ValidationError("Количество должно быть > 0")

        try:
            stock = Stock.objects.get(id=data["stock_id"])
        except Stock.DoesNotExist:
            raise serializers.ValidationError("Акция не найдена")

        try:
            item = PortfolioItem.objects.get(user=user, stock=stock)
        except PortfolioItem.DoesNotExist:
            raise serializers.ValidationError("У вас нет этой акции")

        if item.quantity < data["quantity"]:
            raise serializers.ValidationError("Недостаточно акций")

        data["stock"] = stock
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        stock = validated_data["stock"]
        quantity = validated_data["quantity"]
        total = stock.current_price * quantity

        return Order.objects.create(
            user=user,
            stock=stock,
            type=Order.Type.SELL,
            quantity=quantity,
            price=stock.current_price,
            total=total,
            status=Order.Status.PENDING,
        )


# -------------------------------------
# PORTFOLIO
# -------------------------------------

class PortfolioItemSerializer(serializers.ModelSerializer):
    stock_ticker = serializers.CharField(source="stock.ticker")
    stock_name = serializers.CharField(source="stock.name")
    current_price = serializers.DecimalField(
        source="stock.current_price", max_digits=18, decimal_places=4
    )

    position_value = serializers.SerializerMethodField()
    pnl = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioItem
        fields = [
            "stock_ticker",
            "stock_name",
            "quantity",
            "average_price",
            "current_price",
            "position_value",
            "pnl",
        ]

    def get_position_value(self, obj):
        return obj.quantity * obj.stock.current_price

    def get_pnl(self, obj):
        return obj.quantity * (obj.stock.current_price - obj.average_price)


# -------------------------------------
# NEWS
# -------------------------------------

class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ["id", "title", "text", "image", "created_at"]
