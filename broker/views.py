from rest_framework.views import APIView
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django.utils import timezone
from users.models import UserProfile
from users.permissions import IsStaffForKYC, IsOwnerOrStaff, IsStaff
from .models import (
    BalanceAccount,
    BalanceTransaction,
    Stock,
    Order,
    PortfolioItem,
    News
)
from .serializers import (
    BalanceSerializer,
    BalanceTransactionSerializer,
    StockListSerializer,
    StockDetailSerializer,
    CreateOrderSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    ProcessOrderSerializer,
    CancelOrderSerializer,
    PortfolioItemSerializer,
    CreateSellOrderSerializer,
    NewsSerializer
)


class DepositView(APIView):
    permission_classes = [IsAuthenticated, IsStaffForKYC]  # admin + worker

    def post(self, request):
        user_id = request.data.get("user_id")
        amount = request.data.get("amount")

        if not user_id or not amount:
            return Response({"error": "user_id и amount обязательны"}, status=400)

        try:
            client = UserProfile.objects.get(id=user_id)
        except UserProfile.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)

        account = client.balance
        account.amount += float(amount)
        account.save()

        BalanceTransaction.objects.create(
            user=client,
            type=BalanceTransaction.Type.DEPOSIT,
            amount=amount,
            comment="Пополнение админом/воркером"
        )

        return Response({"message": "Баланс пополнен", "new_balance": account.amount})


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsStaffForKYC]

    def post(self, request):
        user_id = request.data.get("user_id")
        amount = request.data.get("amount")

        if not user_id or not amount:
            return Response({"error": "user_id и amount обязательны"}, status=400)

        try:
            client = UserProfile.objects.get(id=user_id)
        except UserProfile.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)

        account = client.balance

        if account.amount < float(amount):
            return Response({"error": "Недостаточно средств"}, status=400)

        account.amount -= float(amount)
        account.save()

        BalanceTransaction.objects.create(
            user=client,
            type=BalanceTransaction.Type.WITHDRAW,
            amount=amount,
            comment="Вывод средств админом/воркером"
        )

        return Response({"message": "Средства списаны", "new_balance": account.amount})


class BalanceHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BalanceTransactionSerializer

    def get_queryset(self):
        return BalanceTransaction.objects.filter(user=self.request.user).order_by("-created_at")


class StockListView(ListAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockListSerializer
    filter_backends = [SearchFilter]
    search_fields = ["ticker", "name", "gos_number", "description"]


class StockDetailView(RetrieveAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockDetailSerializer


class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        order = serializer.save()

        return Response({
            "message": "Ордер создан",
            "order_id": order.id,
            "total": order.total
        })


class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by("-created_at")
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)


class ProcessOrderView(APIView):
    permission_classes = [IsAuthenticated, IsStaffForKYC]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Ордер не найден"}, status=404)

        serializer = ProcessOrderSerializer(
            data=request.data,
            context={"order": order}
        )
        serializer.is_valid(raise_exception=True)

        updated = serializer.save()

        return Response({
            "message": f"Ордер {updated.status}",
            "order_id": updated.id,
            "status": updated.status
        })


class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Ордер не найден"}, status=404)

        serializer = CancelOrderSerializer(
            data={},
            context={"order": order, "user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            "message": "Ордер отменён",
            "order_id": result.id,
            "status": result.status
        })


class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = PortfolioItem.objects.filter(user=request.user, quantity__gt=0)
        serializer = PortfolioItemSerializer(items, many=True)
        return Response(serializer.data)


class CreateSellOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateSellOrderSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        return Response({
            "message": "Sell ордер создан",
            "order_id": order.id,
            "total": order.total
        })


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Ордер не найден"}, status=404)

        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)


class NewsListView(ListAPIView):
    queryset = News.objects.all().order_by("-created_at")
    serializer_class = NewsSerializer
    filter_backends = [SearchFilter]
    search_fields = ["title", "text"]

class NewsDetailView(RetrieveAPIView):
    queryset = News.objects.all()
    serializer_class = NewsSerializer
