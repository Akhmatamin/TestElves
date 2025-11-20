from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile, PhoneNumberCheck, KYCVerification
from django.contrib.auth.hashers import make_password


class SendSMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class VerifySMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()


class ConfirmPhoneChangeSerializer(serializers.Serializer):
    new_phone_number = serializers.CharField()
    code = serializers.CharField()


class RequestPhoneChangeSerializer(serializers.Serializer):
    new_phone_number = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id','first_name','last_name','otchestvo','phone_number','address','password',]
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        phone = attrs.get("phone_number")
        if not PhoneNumberCheck.objects.filter(phone=phone,is_used=True).exists():
            raise serializers.ValidationError("Phone number is not verified.")
        return attrs

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        validated_data["username"] = validated_data["phone_number"]

        user = UserProfile.objects.create(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect username or password")

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            'users' : {
                'username': instance.username,
                'email': instance.email,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id','first_name', 'last_name', 'otchestvo', 'address']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters")
        return value


class KYCUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCVerification
        fields = ['id','passport_photo_front','passport_photo_back', "selfie_photo"]


class KYCReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["approved", "rejected"])
    reject_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["status"] == "rejected" and not data.get("reject_reason"):
            raise serializers.ValidationError("reject_reason is required for REJECTED status")
        return data
