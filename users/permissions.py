from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsWorker(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "worker"


class IsStaffForKYC(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["admin", "worker"]
        )



class IsKYCApproved(BasePermission):
    message = "Your KYC is not approved"

    def has_permission(self, request, view):
        user = request.user

        # Пользователь должен быть авторизован
        if not user.is_authenticated:
            return False

        # Если нет KYC — доступ запрещён
        if not hasattr(user, "kyc"):
            return False

        # Если статус не approved — доступ запрещён
        return user.kyc.status == "approved"


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["admin", "worker"]
        )

class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ["admin", "worker"]:
            return True
        return obj.user == request.user