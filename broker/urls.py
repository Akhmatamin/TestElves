from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DepositView, WithdrawView, BalanceHistoryView,
    StockListView, StockDetailView,
    CreateOrderView, MyOrdersView, ProcessOrderView, CancelOrderView,
    PortfolioView, CreateSellOrderView, OrderDetailView,
    NewsListView, NewsDetailView
)

urlpatterns = [

    # --- Баланс ---
    path("balance/deposit/", DepositView.as_view(), name="balance-deposit"),
    path("balance/withdraw/", WithdrawView.as_view(), name="balance-withdraw"),
    path("balance/history/", BalanceHistoryView.as_view(), name="balance-history"),

    # --- Акции ---
    path("stocks/", StockListView.as_view(), name="stocks-list"),
    path("stocks/<int:pk>/", StockDetailView.as_view(), name="stocks-detail"),

    # --- Ордера ---
    path("orders/create/", CreateOrderView.as_view(), name="order-create"),
    path("orders/my/", MyOrdersView.as_view(), name="orders-my"),
    path("orders/<int:pk>/process/", ProcessOrderView.as_view(), name="order-process"),
    path("orders/<int:pk>/cancel/", CancelOrderView.as_view(), name="order-cancel"),
    path("orders/sell/", CreateSellOrderView.as_view(), name="order-sell"),
    path("orders/detail/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),

    # --- Портфель ---
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),

    # --- Новости ---
    path("news/", NewsListView.as_view(), name="news-list"),
    path("news/<int:pk>/", NewsDetailView.as_view(), name="news-detail"),
]
