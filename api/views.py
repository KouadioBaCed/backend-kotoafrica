from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login, logout
from .models import (
    User, Supplier, Category, Provenance, Product, ProductImage,
    Order, OrderItem, Payment, Review, QuoteRequest, OTPVerification,
    LogisticsRate, ExchangeRate
)
from .serializers import (
    UserCreateUpdateSerializer, UserSerializer, SupplierSerializer, CategorySerializer,
    ProvenanceSerializer,
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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'products']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products for a given category"""
        category = self.get_object()
        products = Product.objects.filter(category=category, status__in=['active', 'promotion'])
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProvenanceViewSet(viewsets.ModelViewSet):
    queryset = Provenance.objects.all()
    serializer_class = ProvenanceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'products']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products for a given provenance"""
        provenance = self.get_object()
        products = Product.objects.filter(origin=provenance, status__in=['active', 'promotion'])
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['origin', 'category', 'supplier', 'status']
    search_fields = ['name', 'description', 'country']
    ordering_fields = ['price', 'rating', 'created_at']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'popular', 'featured']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductSerializer

    def get_queryset(self):
        # Annoter chaque produit avec le nombre de commandes (hors annulées/remboursées)
        qs = Product.objects.annotate(
            order_count=Count(
                'orderitem',
                filter=Q(orderitem__order__status__in=['pending', 'confirmed', 'shipped', 'available', 'delivered'])
            )
        )
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return qs
        return qs.filter(status__in=['active', 'promotion'])

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular products (3+ orders)"""
        products = Product.objects.filter(
            status__in=['active', 'promotion']
        ).annotate(
            order_count=Count(
                'orderitem',
                filter=Q(orderitem__order__status__in=['pending', 'confirmed', 'shipped', 'available', 'delivered'])
            )
        ).filter(order_count__gte=3).order_by('-order_count', '-rating')[:10]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        products = Product.objects.filter(status__in=['active', 'promotion'], rating__gte=4.5)[:8]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_images(self, request, pk=None):
        """Upload images for a product"""
        product = self.get_object()
        images = request.FILES.getlist('images')

        if not images:
            return Response({'error': 'Aucune image fournie'}, status=status.HTTP_400_BAD_REQUEST)

        has_primary = product.images.filter(is_primary=True).exists()
        created_images = []

        for i, image_file in enumerate(images):
            is_primary = (not has_primary and i == 0)
            img = ProductImage.objects.create(
                product=product,
                image=image_file,
                is_primary=is_primary,
            )
            created_images.append({
                'id': img.id,
                'image': img.image.url,
                'is_primary': img.is_primary,
            })

        return Response(created_images, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='delete_image/(?P<image_id>[^/.]+)', permission_classes=[IsAuthenticated])
    def delete_image(self, request, pk=None, image_id=None):
        """Delete an image from a product"""
        product = self.get_object()
        try:
            image = product.images.get(id=image_id)
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image non trouvée'}, status=status.HTTP_404_NOT_FOUND)

        # Delete the file from storage
        if image.image:
            image.image.delete(save=False)
        image.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_primary_image(self, request, pk=None):
        """Set an image as the primary image for a product"""
        product = self.get_object()
        image_id = request.data.get('image_id')

        if not image_id:
            return Response({'error': 'image_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            image = product.images.get(id=image_id)
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image non trouvée'}, status=status.HTTP_404_NOT_FOUND)

        # Reset all images to non-primary
        product.images.update(is_primary=False)
        # Set the chosen image as primary
        image.is_primary = True
        image.save()

        return Response({'message': 'Image principale mise à jour', 'image_id': image.id})


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'payment_status', 'shipping_method', 'user']
    ordering_fields = ['created_at', 'total']
    search_fields = ['tracking_number', 'user__username', 'user__email']

    def get_queryset(self):
        """
        Les utilisateurs normaux ne voient que leurs propres commandes.
        Les admins voient toutes les commandes, sauf si ?mine=true est passé
        (pour que l'admin puisse voir ses propres commandes en tant que client).
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f'=== OrderViewSet.get_queryset ===')
        logger.info(f'User: {self.request.user}')
        logger.info(f'Is authenticated: {self.request.user.is_authenticated}')
        logger.info(f'Is staff: {self.request.user.is_staff}')

        mine = self.request.query_params.get('mine', '').lower() == 'true'

        if self.request.user.is_staff and not mine:
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def confirm_payment(self, request, pk=None):
        """Admin confirme le paiement Wave reçu (1ère échéance)"""
        if not request.user.is_staff:
            return Response({'error': 'Permission refusée.'}, status=status.HTTP_403_FORBIDDEN)

        order = self.get_object()
        order.paid_amount = order.amount_due
        order.status = 'confirmed'

        if order.payment_mode == 'partial':
            order.payment_status = 'partial'
        else:
            order.payment_status = 'completed'

        order.save()

        Payment.objects.create(
            order=order,
            amount=order.amount_due,
            payment_type='deposit' if order.payment_mode == 'partial' else 'balance',
            payment_method='wave',
            status='completed',
        )

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def confirm_balance(self, request, pk=None):
        """Admin confirme le paiement du solde restant (30%)"""
        if not request.user.is_staff:
            return Response({'error': 'Permission refusée.'}, status=status.HTTP_403_FORBIDDEN)

        order = self.get_object()
        if order.payment_status != 'partial':
            return Response({'error': 'Cette commande n\'a pas de solde en attente.'}, status=status.HTTP_400_BAD_REQUEST)

        remaining = order.total - order.paid_amount
        payment_method = request.data.get('payment_method', 'cash')
        order.paid_amount = order.total
        order.payment_status = 'completed'
        order.save()

        # Si un paiement de solde en attente existe (initié par le client), le marquer comme complété
        pending_balance = Payment.objects.filter(
            order=order,
            payment_type='balance',
            status='pending'
        ).first()

        if pending_balance:
            pending_balance.status = 'completed'
            pending_balance.payment_method = payment_method
            pending_balance.save()
        else:
            Payment.objects.create(
                order=order,
                amount=remaining,
                payment_type='balance',
                payment_method=payment_method,
                status='completed',
            )

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def initiate_balance_payment(self, request, pk=None):
        """Client signale qu'il a initié le paiement du solde (30%) via Wave"""
        import logging
        logger = logging.getLogger(__name__)

        order = self.get_object()

        # Vérifier que c'est bien le propriétaire de la commande
        if order.user != request.user and not request.user.is_staff:
            return Response({'error': 'Permission refusée.'}, status=status.HTTP_403_FORBIDDEN)

        if order.payment_status != 'partial':
            return Response(
                {'error': 'Cette commande n\'a pas de solde en attente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier qu'il n'y a pas déjà un paiement de solde en attente
        existing_pending = Payment.objects.filter(
            order=order,
            payment_type='balance',
            status='pending'
        ).exists()

        if existing_pending:
            return Response(
                {'message': 'Un paiement de solde est déjà en attente de confirmation.'},
                status=status.HTTP_200_OK
            )

        remaining = order.total - order.paid_amount

        # Créer un paiement en attente pour le solde
        Payment.objects.create(
            order=order,
            amount=remaining,
            payment_type='balance',
            payment_method='wave',
            status='pending',
        )

        logger.info(f'Balance payment initiated for order {order.tracking_number} - {remaining} FCFA via Wave')

        serializer = self.get_serializer(order)
        return Response({
            'message': 'Paiement du solde initié. L\'équipe va confirmer la réception.',
            'order': serializer.data
        })

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
        orders = Order.objects.select_related('user').prefetch_related('items__product__images').order_by('-created_at')

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
                    'phone': user_stat.phone,
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

    def destroy(self, request, *args, **kwargs):
        """Supprimer une commande (admin uniquement)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission refusée. Accès admin uniquement.'},
                status=status.HTTP_403_FORBIDDEN
            )
        order = self.get_object()
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_delete(self, request):
        """Supprimer plusieurs commandes (admin uniquement)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission refusée. Accès admin uniquement.'},
                status=status.HTTP_403_FORBIDDEN
            )
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'Aucun ID fourni.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        deleted_count, _ = Order.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted_count})


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

        # Mettre à jour le payment_status de la commande
        payment = serializer.instance
        self.update_order_payment_status(payment.order)

        headers = self.get_success_headers(serializer.data)
        logger.info(f'Paiement créé avec succès: {serializer.data}')
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update_order_payment_status(self, order):
        """
        Met à jour le payment_status de la commande en fonction des paiements complétés
        """
        from django.db.models import Sum

        # Calculer le montant total payé (seulement les paiements complétés)
        total_paid = order.payments.filter(
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # Mettre à jour paid_amount
        order.paid_amount = total_paid

        # Déterminer le payment_status
        if total_paid == 0:
            order.payment_status = 'pending'
        elif total_paid < order.total:
            order.payment_status = 'partial'
        else:
            order.payment_status = 'completed'

        order.save()

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Order {order.tracking_number}: paid_amount={total_paid}, payment_status={order.payment_status}')


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
            approved=Count('id', filter=Q(status='approved')),
            pending=Count('id', filter=Q(status='pending')),
            rejected=Count('id', filter=Q(status='rejected'))
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
            pending=Count('id', filter=Q(status='pending')),
            processing=Count('id', filter=Q(status='processing')),
            quoted=Count('id', filter=Q(status='quoted')),
            accepted=Count('id', filter=Q(status='accepted')),
            rejected=Count('id', filter=Q(status='rejected'))
        )

        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_quotes(self, request):
        """Get current user's quote requests"""
        quotes = QuoteRequest.objects.filter(user=request.user)
        serializer = self.get_serializer(quotes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def accept_quote(self, request, pk=None):
        """Client accepts a validated quote"""
        quote = self.get_object()

        # Vérifier que c'est bien le devis de l'utilisateur
        if quote.user != request.user:
            return Response(
                {'error': 'Vous n\'êtes pas autorisé à accepter ce devis'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Vérifier que le devis a été validé et a un prix
        if quote.status != 'quoted':
            return Response(
                {'error': 'Ce devis n\'a pas encore été validé par l\'administrateur'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not quote.quoted_price:
            return Response(
                {'error': 'Le prix du devis n\'a pas encore été défini'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Passer le devis en statut "accepté"
        quote.status = 'accepted'
        quote.save()

        serializer = self.get_serializer(quote)
        return Response({
            'message': 'Devis accepté avec succès',
            'quote': serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def pay_quote(self, request, pk=None):
        """Process payment for an accepted quote"""
        quote = self.get_object()

        # Vérifier que c'est bien le devis de l'utilisateur
        if quote.user != request.user:
            return Response(
                {'error': 'Vous n\'êtes pas autorisé à payer ce devis'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Vérifier que le devis a été accepté
        if quote.status != 'accepted':
            return Response(
                {'error': 'Vous devez d\'abord accepter le devis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le devis n'a pas déjà été payé
        if quote.payment_status == 'paid':
            return Response(
                {'error': 'Ce devis a déjà été payé'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer les données de paiement
        payment_mode = request.data.get('payment_mode', 'full')  # 'full' ou 'partial'
        payment_method = request.data.get('payment_method')
        shipping_address = request.data.get('shipping_address', {})

        if not payment_method:
            return Response(
                {'error': 'Méthode de paiement requise'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer la commande basée sur le devis
        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address.get('address', ''),
            shipping_city=shipping_address.get('city', ''),
            shipping_country=shipping_address.get('country', ''),
            phone=quote.whatsapp,
            total=float(quote.quoted_price),
            subtotal=float(quote.quoted_price),
            shipping_cost=0.00,
            paid_amount=0.00,
            payment_status='pending'
        )

        # Créer un item de commande pour le devis
        OrderItem.objects.create(
            order=order,
            product=None,  # Pas de produit lié, c'est un devis personnalisé
            quantity=quote.quantity,
            price=float(quote.quoted_price) / quote.quantity,  # Prix unitaire
            custom_description=f"Devis personnalisé: {quote.description}"
        )

        # Calculer le montant à payer selon le mode
        total = float(quote.quoted_price)
        amount_to_pay = round(total if payment_mode == 'full' else total * 0.5, 2)
        remaining_amount = round(total - amount_to_pay, 2)

        # Créer le premier paiement (acompte ou paiement total)
        payment = Payment.objects.create(
            order=order,
            amount=amount_to_pay,
            payment_type='deposit',
            payment_method=payment_method,
            status='completed'  # Considéré comme complété une fois l'action lancée
        )

        # Si paiement partiel, créer un deuxième paiement pour le solde
        if payment_mode == 'partial' and remaining_amount > 0:
            Payment.objects.create(
                order=order,
                amount=remaining_amount,
                payment_type='balance',
                payment_method='cash',  # À la livraison = espèces
                status='pending'
            )

        # Mettre à jour le statut de paiement de la commande
        order.paid_amount = amount_to_pay
        order.payment_status = 'completed' if payment_mode == 'full' else 'partial'
        order.save()

        # Lier le devis à la commande et marquer comme payé
        quote.order = order
        quote.payment_status = 'paid'
        quote.save()

        return Response({
            'message': 'Paiement effectué avec succès',
            'order_id': order.id,
            'payment_id': payment.id,
            'amount_paid': amount_to_pay,
            'remaining_amount': remaining_amount if payment_mode == 'partial' else 0
        }, status=status.HTTP_201_CREATED)


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

    # For password reset, check if user exists
    if purpose == 'password_reset':
        if not User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'message': 'Aucun compte trouvé avec cet email'
            }, status=status.HTTP_404_NOT_FOUND)

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

        # Update password (use update() to avoid triggering custom_id generation)
        User.objects.filter(pk=user.pk).update(password=make_password(new_password))

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
        # Current date + period filter
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = now - timedelta(days=7)

        period = request.GET.get('period', 'all')
        period_start = None
        if period == 'day':
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            period_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'month':
            period_start = current_month_start
        elif period == 'year':
            period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Base queryset for orders (filtered by period if needed)
        base_orders = Order.objects.all()
        if period_start:
            base_orders = base_orders.filter(created_at__gte=period_start)

        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_month = User.objects.filter(date_joined__gte=current_month_start).count()
        admin_users = User.objects.filter(is_staff=True).count()

        # Review statistics
        total_reviews = Review.objects.count()
        approved_reviews = Review.objects.filter(is_approved=True).count()
        pending_reviews = Review.objects.filter(is_approved=False).count()
        avg_rating = Review.objects.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg'] or 0

        # Order statistics (filtered)
        total_orders_count = base_orders.count()
        orders_month = base_orders.filter(created_at__gte=current_month_start).count() if not period_start else total_orders_count

        orders_by_status = base_orders.values('status').annotate(count=Count('id'))
        status_breakdown = {item['status']: item['count'] for item in orders_by_status}

        pending_orders = status_breakdown.get('pending', 0)
        confirmed_orders = status_breakdown.get('confirmed', 0)
        shipped_orders = status_breakdown.get('shipped', 0)
        available_orders = status_breakdown.get('available', 0)
        delivered_orders = status_breakdown.get('delivered', 0)
        cancelled_orders = status_breakdown.get('cancelled', 0)
        refunded_orders = status_breakdown.get('refunded', 0)

        # Revenue statistics (filtered, exclude cancelled and refunded)
        active_orders = base_orders.exclude(status__in=['cancelled', 'refunded'])
        total_revenue = active_orders.aggregate(Sum('total'))['total__sum'] or 0

        revenue_month = active_orders.filter(
            created_at__gte=current_month_start
        ).aggregate(Sum('total'))['total__sum'] or 0 if not period_start else float(total_revenue)

        # Financial stats (filtered)
        total_avances = active_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
        total_reste = float(total_revenue) - float(total_avances)

        refunded_qs = base_orders.filter(status='refunded')
        cancelled_qs = base_orders.filter(status='cancelled')

        # Cash (paiement total 100%)
        cash_orders = active_orders.filter(payment_mode='total')
        cash_stats = {
            'count': cash_orders.count(),
            'total': float(cash_orders.aggregate(Sum('total'))['total__sum'] or 0),
        }

        # Partiel (paiement 70%)
        partial_orders = active_orders.filter(payment_mode='partial')
        partial_paid = float(partial_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0)
        partial_total = float(partial_orders.aggregate(Sum('total'))['total__sum'] or 0)
        partial_stats = {
            'count': partial_orders.count(),
            'total': partial_total,
            'avance': partial_paid,
            'reste': partial_total - partial_paid,
        }

        # Remboursement
        refund_stats = {
            'count': refunded_qs.count(),
            'total': float(refunded_qs.aggregate(Sum('total'))['total__sum'] or 0),
        }

        # Total annulées (cancelled + refunded)
        total_annulees = float((cancelled_qs | refunded_qs).aggregate(Sum('total'))['total__sum'] or 0)

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
                status__in=['cancelled', 'refunded']
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
            'period': period,
            'orders': {
                'total': total_orders_count,
                'this_month': orders_month,
                'pending': pending_orders,
                'confirmed': confirmed_orders,
                'shipped': shipped_orders,
                'available': available_orders,
                'delivered': delivered_orders,
                'cancelled': cancelled_orders,
                'refunded': refunded_orders,
            },
            'revenue': {
                'total': float(total_revenue),
                'this_month': float(revenue_month),
                'total_avances': float(total_avances),
                'reste_a_payer': float(total_reste),
                'total_annulees': float(total_annulees),
                'cash': cash_stats,
                'partial': partial_stats,
                'refunded': refund_stats,
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_export_excel(request):
    """Export dashboard data as Excel file"""
    from django.db.models import Sum, Count
    from datetime import timedelta
    from django.utils import timezone
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO
    import django.http

    if not request.user.is_staff:
        return Response({'error': 'Permission refusée.'}, status=status.HTTP_403_FORBIDDEN)

    now = timezone.now()
    period = request.GET.get('period', 'all')
    period_start = None
    period_label = 'Toutes les périodes'

    if period == 'day':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = f"Aujourd'hui ({now.strftime('%d/%m/%Y')})"
    elif period == 'week':
        period_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = f"Cette semaine (depuis {period_start.strftime('%d/%m/%Y')})"
    elif period == 'month':
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_label = f"Ce mois ({now.strftime('%m/%Y')})"
    elif period == 'year':
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        period_label = f"Cette année ({now.strftime('%Y')})"

    base_orders = Order.objects.all()
    if period_start:
        base_orders = base_orders.filter(created_at__gte=period_start)

    active_orders = base_orders.exclude(status__in=['cancelled', 'refunded'])
    refunded_qs = base_orders.filter(status='refunded')
    cancelled_qs = base_orders.filter(status='cancelled')
    cash_orders = active_orders.filter(payment_mode='total')
    partial_orders = active_orders.filter(payment_mode='partial')

    wb = Workbook()
    header_font = Font(bold=True, color='FFFFFF', size=12)
    header_fill = PatternFill(start_color='1BAA70', end_color='1BAA70', fill_type='solid')
    sub_header_font = Font(bold=True, size=11)
    sub_header_fill = PatternFill(start_color='FFD835', end_color='FFD835', fill_type='solid')
    money_format = '#,##0'
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # === Feuille 1: Résumé comptable ===
    ws = wb.active
    ws.title = 'Comptabilité'
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20

    row = 1
    ws.merge_cells('A1:C1')
    ws['A1'] = f'KÔTO AFRICA - Comptabilité ({period_label})'
    ws['A1'].font = Font(bold=True, size=14, color='4A2C2A')
    ws['A1'].alignment = Alignment(horizontal='center')

    # Compute all values upfront
    ca = float(active_orders.aggregate(Sum('total'))['total__sum'] or 0)
    encaisse = float(active_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0)
    cash_total = float(cash_orders.aggregate(Sum('total'))['total__sum'] or 0)
    cash_paid = float(cash_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0)
    partial_total = float(partial_orders.aggregate(Sum('total'))['total__sum'] or 0)
    partial_paid = float(partial_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0)
    refund_total = float(refunded_qs.aggregate(Sum('total'))['total__sum'] or 0)
    cancel_total = float(cancelled_qs.aggregate(Sum('total'))['total__sum'] or 0)

    ca_fill = PatternFill(start_color='1BAA70', end_color='1BAA70', fill_type='solid')
    ca_font = Font(bold=True, color='FFFFFF', size=12)

    # === Section 1: CHIFFRE D'AFFAIRES TOTAL ===
    row = 3
    ws.merge_cells('A3:C3')
    cell = ws.cell(row=row, column=1, value="CHIFFRE D'AFFAIRES TOTAL")
    cell.font = ca_font
    cell.fill = ca_fill
    cell.alignment = Alignment(horizontal='center')
    cell.border = thin_border
    for col_idx in range(2, 4):
        ws.cell(row=row, column=col_idx).fill = ca_fill
        ws.cell(row=row, column=col_idx).border = thin_border

    row = 4
    for col_idx, title in enumerate(['', 'Nombre', 'Montant (FCFA)'], 1):
        cell = ws.cell(row=row, column=col_idx, value=title)
        cell.font = Font(bold=True, size=10, color='666666')
        cell.border = thin_border

    row = 5
    ws.cell(row=row, column=1, value="CA Total").font = Font(bold=True, size=12)
    ws.cell(row=row, column=2, value=active_orders.count()).font = Font(bold=True, size=12)
    c = ws.cell(row=row, column=3, value=ca)
    c.number_format = money_format
    c.font = Font(bold=True, size=12, color='1BAA70')

    row = 6
    ws.cell(row=row, column=1, value="   dont Cash (100%)").font = Font(size=10)
    ws.cell(row=row, column=2, value=cash_orders.count())
    c = ws.cell(row=row, column=3, value=cash_total)
    c.number_format = money_format

    row = 7
    ws.cell(row=row, column=1, value="   dont Partiel (70%)").font = Font(size=10)
    ws.cell(row=row, column=2, value=partial_orders.count())
    c = ws.cell(row=row, column=3, value=partial_total)
    c.number_format = money_format

    row = 9
    ws.cell(row=row, column=1, value='Total encaissé').font = Font(bold=True)
    ws.cell(row=row, column=2, value=active_orders.count())
    c = ws.cell(row=row, column=3, value=encaisse)
    c.number_format = money_format
    c.font = Font(bold=True, color='1BAA70')

    row = 10
    ws.cell(row=row, column=1, value='Reste à encaisser').font = Font(bold=True)
    ws.cell(row=row, column=2, value=partial_orders.count())
    c = ws.cell(row=row, column=3, value=ca - encaisse)
    c.number_format = money_format
    c.font = Font(bold=True, color='F97316')

    # === Section 2: CASH (100%) ===
    row = 12
    for col_idx, title in enumerate(['CASH (100%)', 'Nombre', 'Montant (FCFA)'], 1):
        cell = ws.cell(row=row, column=col_idx, value=title)
        cell.font = sub_header_font
        cell.fill = sub_header_fill
        cell.border = thin_border

    row = 13
    ws.cell(row=row, column=1, value='Commandes payées 100%')
    ws.cell(row=row, column=2, value=cash_orders.count())
    c = ws.cell(row=row, column=3, value=cash_total)
    c.number_format = money_format

    row = 14
    ws.cell(row=row, column=1, value='Montant encaissé')
    c = ws.cell(row=row, column=3, value=cash_paid)
    c.number_format = money_format

    # === Section 3: PARTIEL (70%) ===
    row = 16
    partial_fill = PatternFill(start_color='F97316', end_color='F97316', fill_type='solid')
    for col_idx, title in enumerate(['PARTIEL (70%)', 'Nombre', 'Montant (FCFA)'], 1):
        cell = ws.cell(row=row, column=col_idx, value=title)
        cell.font = Font(bold=True, size=11, color='FFFFFF')
        cell.fill = partial_fill
        cell.border = thin_border

    row = 17
    ws.cell(row=row, column=1, value='Commandes partielles')
    ws.cell(row=row, column=2, value=partial_orders.count())
    c = ws.cell(row=row, column=3, value=partial_total)
    c.number_format = money_format

    row = 18
    ws.cell(row=row, column=1, value='Avances encaissées (70%)')
    c = ws.cell(row=row, column=3, value=partial_paid)
    c.number_format = money_format
    c.font = Font(color='1BAA70')

    row = 19
    ws.cell(row=row, column=1, value='Reste à encaisser (30%)')
    c = ws.cell(row=row, column=3, value=partial_total - partial_paid)
    c.number_format = money_format
    c.font = Font(bold=True, color='F97316')

    # === Section 4: REMBOURSEMENTS ===
    row = 21
    refund_fill = PatternFill(start_color='EF4444', end_color='EF4444', fill_type='solid')
    for col_idx, title in enumerate(['REMBOURSEMENTS', 'Nombre', 'Montant (FCFA)'], 1):
        cell = ws.cell(row=row, column=col_idx, value=title)
        cell.font = Font(bold=True, size=11, color='FFFFFF')
        cell.fill = refund_fill
        cell.border = thin_border

    row = 22
    ws.cell(row=row, column=1, value='Commandes remboursées')
    ws.cell(row=row, column=2, value=refunded_qs.count())
    c = ws.cell(row=row, column=3, value=refund_total)
    c.number_format = money_format

    # === Section 5: ANNULÉES ===
    row = 23
    ws.cell(row=row, column=1, value='Commandes annulées')
    ws.cell(row=row, column=2, value=cancelled_qs.count())
    c = ws.cell(row=row, column=3, value=cancel_total)
    c.number_format = money_format

    # Bordures pour toutes les cellules de données
    for r in range(3, 24):
        for c_col in range(1, 4):
            cell = ws.cell(row=r, column=c_col)
            if cell.border == Border():
                cell.border = thin_border

    # === Feuille 2: Détail des commandes ===
    ws2 = wb.create_sheet('Détail commandes')
    headers = ['N° Tracking', 'Date', 'Client', 'Statut', 'Mode paiement', 'Total (FCFA)', 'Payé (FCFA)', 'Reste (FCFA)']
    col_widths = [18, 14, 25, 22, 16, 16, 16, 16]
    for i, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws2.cell(row=1, column=i, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        ws2.column_dimensions[chr(64 + i)].width = w

    status_labels = {
        'pending': 'En attente', 'confirmed': 'Confirmé en préparation',
        'shipped': 'Expédié', 'available': 'Disponible à Abidjan',
        'delivered': 'Livré', 'cancelled': 'Annulée', 'refunded': 'Remboursé',
    }

    for idx, order in enumerate(base_orders.select_related('user').order_by('-created_at'), 2):
        total_val = float(order.total or 0)
        paid_val = float(order.paid_amount or 0)
        ws2.cell(row=idx, column=1, value=order.tracking_number).border = thin_border
        ws2.cell(row=idx, column=2, value=order.created_at.strftime('%d/%m/%Y')).border = thin_border
        ws2.cell(row=idx, column=3, value=f'{order.user.first_name} {order.user.last_name}'.strip() or order.user.username).border = thin_border
        ws2.cell(row=idx, column=4, value=status_labels.get(order.status, order.status)).border = thin_border
        ws2.cell(row=idx, column=5, value='Partiel 70%' if order.payment_mode == 'partial' else 'Total 100%').border = thin_border
        c = ws2.cell(row=idx, column=6, value=total_val)
        c.number_format = money_format
        c.border = thin_border
        c = ws2.cell(row=idx, column=7, value=paid_val)
        c.number_format = money_format
        c.border = thin_border
        c = ws2.cell(row=idx, column=8, value=total_val - paid_val)
        c.number_format = money_format
        c.border = thin_border

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f'koto_africa_comptabilite_{now.strftime("%Y%m%d")}.xlsx'
    response = django.http.HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class LogisticsRateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing logistics shipping rates"""
    queryset = LogisticsRate.objects.all()
    serializer_class = LogisticsRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['shipping_method', 'updated_at']
    ordering = ['shipping_method']

    def get_permissions(self):
        """Allow read access to all users, but only authenticated admins can modify"""
        if self.action in ['list', 'retrieve', 'all_rates']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]  # Only authenticated users can modify
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
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
        """Allow read access to all users, but only authenticated admins can modify"""
        if self.action in ['list', 'retrieve', 'current']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]  # Only authenticated users can modify
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
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
