from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, SupplierViewSet, CategoryViewSet,
    ProductViewSet, OrderViewSet, PaymentViewSet, ReviewViewSet,
    QuoteRequestViewSet,
    register_view, login_view, logout_view,
    user_profile_view, update_profile_view
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'quote-requests', QuoteRequestViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Authentication endpoints
    path('auth/register/', register_view, name='register'),
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', user_profile_view, name='user_profile'),
    path('auth/profile/update/', update_profile_view, name='update_profile'),
]
