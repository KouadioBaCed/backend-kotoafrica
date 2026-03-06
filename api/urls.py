from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, SupplierViewSet, CategoryViewSet,
    ProvenanceViewSet, ProductViewSet, OrderViewSet, PaymentViewSet, ReviewViewSet,
    QuoteRequestViewSet, LogisticsRateViewSet, ExchangeRateViewSet,
    register_view, login_view, logout_view,
    user_profile_view, update_profile_view,
    send_otp_view, verify_otp_view, register_with_otp_view, update_password_view,
    dashboard_statistics,
    dashboard_export_excel
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'provenances', ProvenanceViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'quote-requests', QuoteRequestViewSet)
router.register(r'logistics-rates', LogisticsRateViewSet)
router.register(r'exchange-rates', ExchangeRateViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Authentication endpoints
    path('auth/register/', register_view, name='register'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', user_profile_view, name='user_profile'),
    path('auth/profile/update/', update_profile_view, name='update_profile'),

    # OTP Email Verification endpoints
    path('auth/send-otp/', send_otp_view, name='send_otp'),
    path('auth/verify-otp/', verify_otp_view, name='verify_otp'),
    path('auth/register-with-otp/', register_with_otp_view, name='register_with_otp'),
    path('auth/update-password/', update_password_view, name='update_password'),

    # Dashboard statistics
    path('dashboard/statistics/', dashboard_statistics, name='dashboard_statistics'),
    path('dashboard/export/', dashboard_export_excel, name='dashboard_export_excel'),
]
