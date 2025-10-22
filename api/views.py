from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from django.contrib.auth import login, logout
from .models import (
    User, Supplier, Category, Product, ProductImage,
    Order, OrderItem, Payment, Review, QuoteRequest
)
from .serializers import (
    UserSerializer, SupplierSerializer, CategorySerializer,
    ProductSerializer, ProductCreateSerializer,
    OrderSerializer, OrderCreateSerializer,
    PaymentSerializer, PaymentCreateSerializer,
    ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    QuoteRequestSerializer, QuoteRequestCreateSerializer,
    RegisterSerializer, LoginSerializer, UserProfileSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'custom_id']
    ordering_fields = ['date_joined', 'username']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['supplier_type', 'verified', 'country']
    search_fields = ['company_name', 'country']


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['origin', 'category', 'supplier']
    search_fields = ['name', 'description', 'country']
    ordering_fields = ['price', 'rating', 'created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductSerializer

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular products"""
        products = self.get_queryset().order_by('-rating', '-reviews_count')[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        products = self.get_queryset().filter(rating__gte=4.5)[:8]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'payment_status', 'shipping_method', 'user']
    ordering_fields = ['created_at', 'total']
    search_fields = ['tracking_number', 'user__username', 'user__email']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        new_status = request.data.get('status')

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            serializer = self.get_serializer(order)
            return Response(serializer.data)

        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def local_products(self, request):
        """Get orders for local products only"""
        local_orders = self.get_queryset().filter(shipping_method='local')
        serializer = self.get_serializer(local_orders, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_type', 'payment_method', 'order']
    ordering_fields = ['created_at', 'amount']

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating', 'user', 'status']
    ordering_fields = ['created_at', 'rating']

    def get_queryset(self):
        """Return approved reviews by default, all reviews for admin"""
        queryset = super().get_queryset()
        # If not admin, filter to only approved reviews
        if not self.request.user.is_staff:
            queryset = queryset.filter(status='approved')
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ReviewUpdateSerializer
        return ReviewSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a review (admin only)"""
        review = self.get_object()
        review.status = 'approved'
        review.save()
        serializer = self.get_serializer(review)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a review (admin only)"""
        review = self.get_object()
        review.status = 'rejected'
        review.save()
        serializer = self.get_serializer(review)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Add admin reply to a review (admin only)"""
        review = self.get_object()
        admin_reply = request.data.get('admin_reply')

        if admin_reply:
            review.admin_reply = admin_reply
            review.save()
            serializer = self.get_serializer(review)
            return Response(serializer.data)

        return Response(
            {'error': 'admin_reply field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending reviews for moderation (admin only)"""
        pending_reviews = Review.objects.filter(status='pending')
        serializer = self.get_serializer(pending_reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get review statistics"""
        from django.db.models import Avg, Count

        stats = Review.objects.aggregate(
            total=Count('id'),
            average_rating=Avg('rating'),
            approved=Count('id', filter=models.Q(status='approved')),
            pending=Count('id', filter=models.Q(status='pending')),
            rejected=Count('id', filter=models.Q(status='rejected'))
        )

        # Rating distribution
        rating_dist = {}
        for i in range(1, 6):
            rating_dist[f'rating_{i}'] = Review.objects.filter(rating=i).count()

        stats['rating_distribution'] = rating_dist

        return Response(stats)


class QuoteRequestViewSet(viewsets.ModelViewSet):
    queryset = QuoteRequest.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'gender']
    ordering_fields = ['created_at', 'quantity']
    search_fields = ['full_name', 'whatsapp', 'description']

    def get_serializer_class(self):
        if self.action == 'create':
            return QuoteRequestCreateSerializer
        return QuoteRequestSerializer

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update quote request status"""
        quote = self.get_object()
        new_status = request.data.get('status')

        if new_status in dict(QuoteRequest.STATUS_CHOICES):
            quote.status = new_status

            # Update notes if provided
            notes = request.data.get('notes')
            if notes:
                quote.notes = notes

            quote.save()
            serializer = self.get_serializer(quote)
            return Response(serializer.data)

        return Response(
            {'error': 'Invalid status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get quote request statistics"""
        from django.db.models import Count

        stats = QuoteRequest.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(status='pending')),
            processing=Count('id', filter=models.Q(status='processing')),
            quoted=Count('id', filter=models.Q(status='quoted')),
            accepted=Count('id', filter=models.Q(status='accepted')),
            rejected=Count('id', filter=models.Q(status='rejected'))
        )

        return Response(stats)


# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Register a new user"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Compte créé avec succès!'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login user and return JWT tokens"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Connexion réussie!'
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout user by blacklisting the refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        return Response({
            'message': 'Déconnexion réussie!'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    """Get current user profile"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """Update current user profile"""
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'user': serializer.data,
            'message': 'Profil mis à jour avec succès!'
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
