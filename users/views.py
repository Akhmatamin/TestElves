from django.utils import timezone
from rest_framework.generics import UpdateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UserProfile, PhoneNumberCheck, KYCVerification
from .permissions import IsStaffForKYC
from .utils import generate_otp, send_sms
from .serializers import (
    SendSMSSerializer,
    VerifySMSSerializer,
    RegisterSerializer, UpdateProfileSerializer, ChangePasswordSerializer, KYCUploadSerializer, KYCReviewSerializer,
    RequestPhoneChangeSerializer, ConfirmPhoneChangeSerializer
)



# 1. Отправка SMS
class SendSMSView(APIView):
    def post(self, request):
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone_number"]

        code = generate_otp()
        PhoneNumberCheck.objects.create(phone=phone, code=code)

        send_sms(phone, code)

        return Response({"message": "SMS sent"}, status=200)


# 2. Проверка SMS
class VerifySMSView(APIView):
    def post(self, request):
        serializer = VerifySMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]

        try:
            otp = PhoneNumberCheck.objects.filter(
                phone=phone,
                code=code,
                is_used=False
            ).latest("created_at")
        except PhoneNumberCheck.DoesNotExist:
            return Response({"error": "Invalid code"}, status=400)

        if otp.is_expired():
            return Response({"error": "Code expired"}, status=400)

        otp.is_used = True
        otp.save()

        return Response({"message": "Phone verified"}, status=200)


class RequestPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RequestPhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_phone = serializer.validated_data["new_phone_number"]

        # Нельзя менять на тот же номер
        if new_phone == request.user.phone_number:
            return Response({"error": "This is already your phone number"}, status=400)

        # Проверяем, что новый номер не занят
        if UserProfile.objects.filter(phone_number=new_phone).exists():
            return Response({"error": "Phone number already taken"}, status=400)

        # Генерируем и сохраняем OTP
        code = generate_otp()
        PhoneNumberCheck.objects.create(phone=new_phone, code=code)

        send_sms(new_phone, code)

        return Response({"message": "Verification code sent to new phone"})


class ConfirmPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConfirmPhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_phone = serializer.validated_data["new_phone_number"]
        code = serializer.validated_data["code"]

        try:
            otp = PhoneNumberCheck.objects.filter(
                phone=new_phone,
                code=code,
                is_used=False
            ).latest("created_at")
        except PhoneNumberCheck.DoesNotExist:
            return Response({"error": "Invalid code"}, status=400)

        # Проверка на срок действия
        if otp.is_expired():
            return Response({"error": "Code expired"}, status=400)

        otp.is_used = True
        otp.save()

        # Меняем номер в аккаунте
        user = request.user
        old_phone = user.phone_number

        user.phone_number = new_phone
        user.username = new_phone
        user.save()

        # Инвалидируем токены (чтобы был свежий логин)
        refresh = RefreshToken.for_user(user)
        refresh.blacklist()

        return Response({
            "message": "Phone number changed successfully. Please login again.",
            "old_phone": old_phone,
            "new_phone": new_phone,
        })


# 3. Регистрация
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response({
            "message": "Registration successful",
            "user_id": user.id
        }, status=201)


# 4. Логин (телефон + пароль)
class LoginView(APIView):
    def post(self, request):
        phone = request.data.get("phone_number")
        password = request.data.get("password")

        if not phone or not password:
            return Response({"error": "phone_number and password required"}, status=400)
        user = authenticate(username=phone, password=password)
        if not user:
            return Response({"error": "Invalid phone or password"}, status=400)
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user.id,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        })

class LogoutView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# Create your views here.

class ProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = UpdateProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]
        # Проверяем старый пароль
        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=400)
        # Меняем пароль
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password changed successfully"}, status=200)



class KYCUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        user = request.user
        # Проверяем, может ли он загружать повторно
        if hasattr(user, "kyc") and user.kyc.status in ["pending", "approved"]:
            return Response({"error": "KYC already submitted"}, status=400)

        serializer = KYCUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kyc = KYCVerification.objects.create(
            user=user,
            passport_photo_front=request.data["passport_photo_front"],
            passport_photo_back=request.data["passport_photo_back"],
            selfie_photo=request.data["selfie_photo"],
        )

        return Response({"message": "KYC submitted successfully", "status": kyc.status})


class KYCStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not hasattr(user, "kyc"):
            return Response({"status": "not_submitted"})

        return Response({
            "status": user.kyc.status,
            "reject_reason": user.kyc.reject_reason
        })


class KYCListView(ListAPIView):
    queryset = KYCVerification.objects.all()
    serializer_class = KYCUploadSerializer
    permission_classes = [IsStaffForKYC]

class KYCDetailView(APIView):
    permission_classes = [IsStaffForKYC]
    def get(self, request, pk):
        try:
            kyc = KYCVerification.objects.get(pk=pk)
        except KYCVerification.DoesNotExist:
            return Response({"error": "KYC not found"}, status=404)

        serializer = KYCUploadSerializer(kyc)
        return Response(serializer.data)



class KYCReviewView(APIView):
    permission_classes = [IsStaffForKYC]
    def post(self, request, pk):
        try:
            kyc = KYCVerification.objects.get(pk=pk)
        except KYCVerification.DoesNotExist:
            return Response({"error": "KYC not found"}, status=404)

        serializer = KYCReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_ = serializer.validated_data["status"]
        reject_reason = serializer.validated_data.get("reject_reason", "")
        kyc.status = status_
        kyc.reject_reason = reject_reason if status_ == "rejected" else ""
        kyc.reviewed_at = timezone.now()
        kyc.save()

        return Response({
            "message": f"KYC {status_} successfully",
            "users": kyc.user.full_name()
        })