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
    Order, OrderItem, Payment, Review, QuoteRequest, OTPVerification,
    LogisticsRate, ExchangeRate
)
from .serializers import (
    UserCreateUpdateSerializer, UserSerializer, SupplierSerializer, CategorySerializer,
    ProductSerializer, ProductCreateSerializer,
    OrderSerializer, OrderCreateSerializer,
    PaymentSerializer, PaymentCreateSerializer,
    ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    QuoteRequestSerializer, QuoteRequestCreateSerializer,
    RegisterSerializer, LoginSerializer, UserProfileSerializer,
    LogisticsRateSerializer, ExchangeRateSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'custom_id']
    ordering_fields = ['date_joined', 'username']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'me']:
            from .serializers import UserCreateUpdateSerializer
            return UserCreateUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get or update current user profile"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f'=== /users/me/ endpoint called ===')
        logger.info(f'Method: {request.method}')
        logger.info(f'User: {request.user.username} (ID: {request.user.id})')

        if request.method == 'GET':
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            logger.info(f'Data received: {request.data}')

            # Use UserCreateUpdateSerializer for updates but exclude password
            data = request.data.copy()
            data.pop('password', None)  # Don't allow password change here
            data.pop('is_staff', None)  # Don't allow is_staff change
            data.pop('is_active', None)  # Don't allow is_active change
            data.pop('user_type', None)  # Don't allow user_type change

            logger.info(f'Data after filtering: {data}')

            serializer = UserCreateUpdateSerializer(request.user, data=data, partial=True)
            if serializer.is_valid():
                logger.info('Serializer is valid, saving...')
                user = serializer.save()
                # Return full user data with UserSerializer
                output_serializer = UserSerializer(user)
                logger.info(f'User updated successfully: {output_serializer.data}')
                return Response(output_serializer.data)

            logger.error(f'Validation errors: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

    def get_queryset(self):
        """
        Les utilisateurs normaux ne voient que leurs propres commandes.
        Les admins voient toutes les commandes.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f'=== OrderViewSet.get_queryset ===')
        logger.info(f'User: {self.request.user}')
        logger.info(f'Is authenticated: {self.request.user.is_authenticated}')
        logger.info(f'Is staff: {self.request.user.is_staff}')

        if self.request.user.is_staff:
            queryset = Order.objects.all()
            logger.info(f'Admin - Retourne toutes les commandes: {queryset.count()}')
            return queryset

        queryset = Order.objects.filter(user=self.request.user)
        logger.info(f'User - Retourne les commandes de {self.request.user.username}: {queryset.count()}')
        return queryset

    def get_permissions(self):
        """
        Nécessite l'authentification pour créer, modifier ou voir les commandes
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'list', 'retrieve']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        """Create order and return full order details"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info('=== Création de commande ===')
        logger.info(f'Utilisateur connecté: {request.user.username} (ID: {request.user.id})')
        logger.info(f'Is authenticated: {request.user.is_authenticated}')
        logger.info(f'Données reçues: {request.data}')

        # Utiliser OrderCreateSerializer pour valider et créer
        # Le contexte est automatiquement passé par get_serializer() qui inclut la request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Créer la commande - le serializer utilisera request.user du contexte
        order = serializer.save()

        logger.info(f'Commande créée: {order.id} - {order.tracking_number} pour user {order.user.username} (ID: {order.user.id})')

        # Retourner les données complètes avec OrderSerializer
        output_serializer = OrderSerializer(order)
        headers = self.get_success_headers(output_serializer.data)

        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update order status (admin only)"""
        import logging
        logger = logging.getLogger(__name__)

        # Vérifier que l'utilisateur est admin
        if not request.user.is_staff:
            logger.warning(f'User {request.user.username} tried to update order status without admin rights')
            return Response(
                {'error': 'Permission refusée. Accès admin uniquement.'},
                status=status.HTTP_403_FORBIDDEN
            )

        order = self.get_object()
        new_status = request.data.get('status')

        logger.info(f'Admin {request.user.username} updating order {order.tracking_number} status from {order.status} to {new_status}')

        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            order.save()

            logger.info(f'Order {order.tracking_number} status updated successfully')

            serializer = self.get_serializer(order)
            return Response(serializer.data)

        logger.error(f'Invalid status: {new_status}')
        return Response(
            {'error': f'Statut invalide: {new_status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def local_products(self, request):
        """Get orders for local products only"""
        local_orders = self.get_queryset().filter(shipping_method='local')
        serializer = self.get_serializer(local_orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def by_user(self, request):
        """Get all orders grouped by user (admin only)"""
        from django.db.models import Count, Sum
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f'=== Orders by user ===')
        logger.info(f'Requester: {request.user.username} (Staff: {request.user.is_staff})')

        # Vérifier que l'utilisateur est admin
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission refusée. Accès admin uniquement.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Récupérer toutes les commandes avec les informations utilisateur
        orders = Order.objects.select_related('user').order_by('-created_at')

        # Grouper par utilisateur
        users_stats = User.objects.annotate(
            total_orders=Count('orders'),
            total_spent=Sum('orders__total'),
            total_paid=Sum('orders__paid_amount')
        ).filter(total_orders__gt=0).order_by('-total_orders')

        # Construire la réponse
        result = []
        for user_stat in users_stats:
            user_orders = orders.filter(user=user_stat)
            result.append({
                'user': {
                    'id': user_stat.id,
                    'username': user_stat.username,
                    'email': user_stat.email,
                    'first_name': user_stat.first_name,
                    'last_name': user_stat.last_name,
                    'custom_id': user_stat.custom_id,
                },
                'statistics': {
                    'total_orders': user_stat.total_orders,
                    'total_spent': float(user_stat.total_spent) if user_stat.total_spent else 0,
                    'total_paid': float(user_stat.total_paid) if user_stat.total_paid else 0,
                },
                'orders': OrderSerializer(user_orders, many=True).data
            })

        logger.info(f'Retourne les commandes de {len(result)} utilisateurs')

        return Response({
            'count': len(result),
            'results': result
        })


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_type', 'payment_method', 'order']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        """
        Les utilisateurs normaux ne voient que les paiements de leurs propres commandes.
        Les admins voient tous les paiements.
        """
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(order__user=self.request.user)

    def get_permissions(self):
        """
        Nécessite l'authentification pour créer, modifier ou voir les paiements
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'list', 'retrieve']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        """Create a new payment with detailed logging"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info('=== Création de paiement ===')
        logger.info(f'Utilisateur: {request.user.username}')
        logger.info(f'Données reçues: {request.data}')

        # Vérifier que la commande appartient à l'utilisateur
        order_id = request.data.get('order')
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                if order.user != request.user and not request.user.is_staff:
                    logger.error(f'La commande {order_id} n\'appartient pas à l\'utilisateur {request.user.username}')
                    return Response(
                        {'order': 'Cette commande ne vous appartient pas'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                logger.info(f'Commande trouvée: {order.tracking_number}')
            except Order.DoesNotExist:
                logger.error(f'Commande {order_id} non trouvée')
                return Response(
                    {'order': 'Commande non trouvée'},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f'Erreurs de validation: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        logger.info(f'Paiement créé avec succès: {serializer.data}')
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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


# ============================================================
# OTP Email Verification Views
# ============================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp_view(request):
    """Send OTP to email for verification"""
    import re
    from django.core.mail import send_mail
    from django.conf import settings
    from django.utils import timezone
    from datetime import timedelta
    import jwt

    email = request.data.get('email')
    purpose = request.data.get('purpose')

    if not email or not purpose:
        return Response({
            'success': False,
            'message': 'Email et objectif requis'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate email format
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        return Response({
            'success': False,
            'message': 'Email invalide'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate purpose
    if purpose not in ['registration', 'password_reset']:
        return Response({
            'success': False,
            'message': 'Objectif invalide'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Rate limiting: max 3 OTP per hour per email
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_attempts = OTPVerification.objects.filter(
        email=email,
        created_at__gte=one_hour_ago
    ).count()

    if recent_attempts >= 3:
        return Response({
            'success': False,
            'message': 'Trop de tentatives. Réessayez dans 1 heure.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # Generate OTP
    otp = OTPVerification.generate_otp()

    # Save OTP in database
    otp_record = OTPVerification.objects.create(
        email=email,
        otp=otp,
        purpose=purpose
    )

    # Prepare email message
    subject = 'Code de vérification KÔTO AFRICA'

    if purpose == 'registration':
        message = f"""
Bonjour,

Votre code de vérification pour créer votre compte KÔTO AFRICA est :

{otp}

Ce code est valide pendant 5 minutes.

Si vous n'avez pas demandé ce code, ignorez cet email.

Cordialement,
L'équipe KÔTO AFRICA
        """
    else:  # password_reset
        message = f"""
Bonjour,

Votre code de vérification pour réinitialiser votre mot de passe KÔTO AFRICA est :

{otp}

Ce code est valide pendant 5 minutes.

Si vous n'avez pas demandé ce code, ignorez cet email.

Cordialement,
L'équipe KÔTO AFRICA
        """

    # Send email
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({
            'success': True,
            'message': 'Code de vérification envoyé par email'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # Delete OTP if email failed
        otp_record.delete()

        return Response({
            'success': False,
            'message': f"Erreur lors de l'envoi : {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_view(request):
    """Verify OTP code"""
    import jwt
    from django.conf import settings
    from datetime import datetime, timedelta

    email = request.data.get('email')
    otp = request.data.get('otp')
    purpose = request.data.get('purpose')

    if not all([email, otp, purpose]):
        return Response({
            'success': False,
            'message': 'Tous les champs sont requis'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Find most recent unverified OTP
    try:
        otp_record = OTPVerification.objects.filter(
            email=email,
            purpose=purpose,
            is_verified=False
        ).order_by('-created_at').first()

        if not otp_record:
            return Response({
                'success': False,
                'message': 'Aucun code trouvé pour cet email'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if expired
        if otp_record.is_expired():
            return Response({
                'success': False,
                'message': 'Le code a expiré. Demandez un nouveau code.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check attempts limit
        if otp_record.attempts >= 5:
            return Response({
                'success': False,
                'message': 'Trop de tentatives. Demandez un nouveau code.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Increment attempts
        otp_record.attempts += 1

        # Verify OTP
        if otp_record.otp != otp:
            otp_record.save()
            return Response({
                'success': False,
                'message': 'Code incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mark as verified and generate token
        otp_record.is_verified = True

        # Generate verification token (valid for 10 minutes)
        verification_token = jwt.encode({
            'email': email,
            'purpose': purpose,
            'otp_id': otp_record.id,
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }, settings.SECRET_KEY, algorithm='HS256')

        otp_record.verification_token = verification_token
        otp_record.save()

        return Response({
            'success': True,
            'message': 'Code vérifié avec succès',
            'verification_token': verification_token
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Erreur : {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_with_otp_view(request):
    """Register user after OTP verification"""
    import jwt
    from django.conf import settings
    from django.contrib.auth.hashers import make_password

    verification_token = request.data.get('verification_token')

    if not verification_token:
        return Response({
            'message': 'Token de vérification requis'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Verify token
    try:
        payload = jwt.decode(verification_token, settings.SECRET_KEY, algorithms=['HS256'])
        email = payload.get('email')

        # Check that token is for registration
        if payload.get('purpose') != 'registration':
            return Response({
                'message': 'Token invalide'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check that OTP was verified
        otp_record = OTPVerification.objects.filter(
            email=email,
            verification_token=verification_token,
            is_verified=True
        ).first()

        if not otp_record:
            return Response({
                'message': 'Token de vérification invalide'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check that email matches
        if request.data.get('email') != email:
            return Response({
                'message': "L'email ne correspond pas"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response({
                'message': 'Un compte existe déjà avec cet email'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if username exists
        username = request.data.get('username')
        if User.objects.filter(username=username).exists():
            return Response({
                'message': 'Ce nom d\'utilisateur est déjà pris'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check password match
        password = request.data.get('password')
        password2 = request.data.get('password2')
        if password != password2:
            return Response({
                'message': 'Les mots de passe ne correspondent pas'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = User.objects.create(
            username=username,
            email=email,
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', ''),
            phone=request.data.get('phone', ''),
            address=request.data.get('address', ''),
            postal_code=request.data.get('postal_code', ''),
            city=request.data.get('city', ''),
            country=request.data.get('country', 'Côte d\'Ivoire'),
            password=make_password(password)
        )

        # Delete used OTP
        otp_record.delete()

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

    except jwt.ExpiredSignatureError:
        return Response({
            'message': 'Le token a expiré. Recommencez la procédure.'
        }, status=status.HTTP_400_BAD_REQUEST)
    except jwt.InvalidTokenError:
        return Response({
            'message': 'Token invalide'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'message': f'Erreur : {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_password_view(request):
    """Update password after OTP verification"""
    import jwt
    from django.conf import settings
    from django.contrib.auth.hashers import make_password

    new_password = request.data.get('new_password')
    verification_token = request.data.get('verification_token')

    if not all([new_password, verification_token]):
        return Response({
            'message': 'Tous les champs sont requis'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Verify token
        payload = jwt.decode(verification_token, settings.SECRET_KEY, algorithms=['HS256'])
        email = payload.get('email')

        # Check that token is for password reset
        if payload.get('purpose') != 'password_reset':
            return Response({
                'message': 'Token invalide'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check that OTP was verified
        otp_record = OTPVerification.objects.filter(
            email=email,
            verification_token=verification_token,
            is_verified=True
        ).first()

        if not otp_record:
            return Response({
                'message': 'Token de vérification invalide'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find user by email
        user = User.objects.filter(email=email).first()

        if not user:
            return Response({
                'message': 'Utilisateur non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)

        # Update password
        user.password = make_password(new_password)
        user.save()

        # Delete used OTP
        otp_record.delete()

        return Response({
            'success': True,
            'message': 'Mot de passe modifié avec succès'
        }, status=status.HTTP_200_OK)

    except jwt.ExpiredSignatureError:
        return Response({
            'message': 'Le token a expiré. Recommencez la procédure.'
        }, status=status.HTTP_400_BAD_REQUEST)
    except jwt.InvalidTokenError:
        return Response({
            'message': 'Token invalide'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'message': f'Erreur : {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_statistics(request):
    """Get global statistics for admin dashboard"""
    from django.db.models import Count, Sum, Q, Avg
    from datetime import datetime, timedelta
    from django.utils import timezone

    try:
        # Current date
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = now - timedelta(days=7)

        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_month = User.objects.filter(date_joined__gte=current_month_start).count()
        admin_users = User.objects.filter(is_staff=True).count()

        # Product statistics (static products from data/products.ts)
        # Since products are static, we'll just count reviews and orders
        total_reviews = Review.objects.count()
        approved_reviews = Review.objects.filter(is_approved=True).count()
        pending_reviews = Review.objects.filter(is_approved=False).count()
        avg_rating = Review.objects.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg'] or 0

        # Order statistics
        total_orders = Order.objects.count()
        orders_month = Order.objects.filter(created_at__gte=current_month_start).count()

        orders_by_status = Order.objects.values('status').annotate(count=Count('id'))
        status_breakdown = {item['status']: item['count'] for item in orders_by_status}

        pending_orders = status_breakdown.get('pending', 0)
        confirmed_orders = status_breakdown.get('confirmed', 0)
        shipped_orders = status_breakdown.get('shipped', 0)
        delivered_orders = status_breakdown.get('delivered', 0)
        cancelled_orders = status_breakdown.get('cancelled', 0)

        # Revenue statistics
        total_revenue = Order.objects.exclude(
            status='cancelled'
        ).aggregate(Sum('total'))['total__sum'] or 0

        revenue_month = Order.objects.filter(
            created_at__gte=current_month_start
        ).exclude(
            status='cancelled'
        ).aggregate(Sum('total'))['total__sum'] or 0

        # Quote request statistics
        total_quotes = QuoteRequest.objects.count()
        quotes_by_status = QuoteRequest.objects.values('status').annotate(count=Count('id'))
        quotes_breakdown = {item['status']: item['count'] for item in quotes_by_status}

        pending_quotes = quotes_breakdown.get('pending', 0)
        processing_quotes = quotes_breakdown.get('processing', 0)
        quoted_quotes = quotes_breakdown.get('quoted', 0)
        accepted_quotes = quotes_breakdown.get('accepted', 0)
        rejected_quotes = quotes_breakdown.get('rejected', 0)

        # Sales data for last 7 days
        sales_last_7_days = []
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            orders_count = Order.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()

            revenue = Order.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).exclude(
                status='cancelled'
            ).aggregate(Sum('total'))['total__sum'] or 0

            sales_last_7_days.append({
                'date': day.strftime('%Y-%m-%d'),
                'orders': orders_count,
                'revenue': float(revenue)
            })

        return Response({
            'users': {
                'total': total_users,
                'active': active_users,
                'new_this_month': new_users_month,
                'admins': admin_users,
            },
            'orders': {
                'total': total_orders,
                'this_month': orders_month,
                'pending': pending_orders,
                'confirmed': confirmed_orders,
                'shipped': shipped_orders,
                'delivered': delivered_orders,
                'cancelled': cancelled_orders,
            },
            'revenue': {
                'total': float(total_revenue),
                'this_month': float(revenue_month),
            },
            'reviews': {
                'total': total_reviews,
                'approved': approved_reviews,
                'pending': pending_reviews,
                'average_rating': round(float(avg_rating), 2),
            },
            'quotes': {
                'total': total_quotes,
                'pending': pending_quotes,
                'processing': processing_quotes,
                'quoted': quoted_quotes,
                'accepted': accepted_quotes,
                'rejected': rejected_quotes,
            },
            'sales_last_7_days': sales_last_7_days,
        })

    except Exception as e:
        return Response({
            'error': f'Erreur lors du calcul des statistiques: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogisticsRateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing logistics shipping rates"""
    queryset = LogisticsRate.objects.all()
    serializer_class = LogisticsRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['shipping_method', 'updated_at']
    ordering = ['shipping_method']

    def get_permissions(self):
        """Allow read access to all authenticated users, but only admins can modify"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]  # Add admin check here if needed
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def all_rates(self, request):
        """Get all active logistics rates with exchange rate"""
        try:
            rates = LogisticsRate.objects.filter(is_active=True)
            exchange_rate = ExchangeRate.get_current_rate()

            rates_data = LogisticsRateSerializer(rates, many=True).data

            return Response({
                'rates': rates_data,
                'usd_to_fcfa': float(exchange_rate)
            })
        except Exception as e:
            return Response({
                'error': f'Erreur lors de la récupération des tarifs: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing currency exchange rates"""
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_permissions(self):
        """Allow read access to all authenticated users, but only admins can modify"""
        if self.action in ['list', 'retrieve', 'current']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]  # Add admin check here if needed
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current active exchange rate"""
        try:
            rate = ExchangeRate.objects.filter(is_active=True).first()
            if rate:
                return Response(ExchangeRateSerializer(rate).data)
            else:
                # Return default rate if none exists
                return Response({
                    'usd_to_fcfa': '661.28',
                    'is_active': True
                })
        except Exception as e:
            return Response({
                'error': f'Erreur lors de la récupération du taux de change: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """Create new exchange rate and deactivate previous ones"""
        # Désactiver tous les taux précédents
        ExchangeRate.objects.filter(is_active=True).update(is_active=False)
        return super().create(request, *args, **kwargs)
