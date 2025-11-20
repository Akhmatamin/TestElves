from django.urls import path
from .views import SendSMSView, VerifySMSView, RegisterView, LoginView, LogoutView, ProfileView, ChangePasswordView, \
    KYCUploadView, KYCStatusView, RequestPhoneChangeView, ConfirmPhoneChangeView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("send-sms/", SendSMSView.as_view()),
    path("verify-sms/", VerifySMSView.as_view()),
    path("change-phone/request/", RequestPhoneChangeView.as_view()),
    path("change-phone/confirm/", ConfirmPhoneChangeView.as_view()),
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("kyc/upload/", KYCUploadView.as_view()),
    path("kyc/status/", KYCStatusView.as_view()),
    path('profile/',ProfileView.as_view(),name='ProfileView'),
    path('change-password/', ChangePasswordView.as_view()),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
