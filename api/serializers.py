from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Supplier, Category, Product, ProductImage,
    Order, OrderItem, Payment, Review, QuoteRequest,
    LogisticsRate, ExchangeRate
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'phone', 'address', 'postal_code', 'city',
                  'country', 'custom_id', 'date_joined', 'last_login', 'is_staff', 'is_active']
        read_only_fields = ['id', 'custom_id', 'date_joined', 'last_login']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'phone', 'address', 'postal_code', 'city',
                  'country', 'password', 'is_staff', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class SupplierSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Supplier
        fields = ['id', 'user', 'supplier_type', 'company_name', 'country',
                  'rating', 'products_count', 'verified', 'last_sync']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary']


class ProductSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'supplier', 'category', 'name', 'description', 'price',
                  'origin', 'country', 'stock', 'rating', 'reviews_count',
                  'delivery_time', 'is_active', 'created_at', 'updated_at', 'images']


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'origin',
                  'country', 'stock', 'delivery_time', 'is_active']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'product_url', 'product_description', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'tracking_number', 'status', 'payment_status',
                  'shipping_method', 'total', 'paid_amount', 'shipping_address',
                  'shipping_fee', 'created_at', 'updated_at', 'items']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Order
        fields = ['shipping_address', 'shipping_fee', 'shipping_method', 'items']

    def create(self, validated_data):
        from decimal import Decimal
        import logging
        logger = logging.getLogger(__name__)

        items_data = validated_data.pop('items')

        # Récupérer l'utilisateur depuis le context (fourni par la vue)
        request = self.context.get('request')
        user = request.user if request else None

        logger.info(f'OrderCreateSerializer.create - Request: {request}')
        logger.info(f'OrderCreateSerializer.create - User from context: {user}')
        logger.info(f'OrderCreateSerializer.create - User authenticated: {user.is_authenticated if user else False}')

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Utilisateur non authentifié")

        logger.info(f'OrderCreateSerializer.create - Création pour user: {user.username} (ID: {user.id})')

        # Calculer le total AVANT de créer la commande
        subtotal = Decimal('0')
        for item_data in items_data:
            # Utiliser le prix fourni par le frontend
            price = Decimal(str(item_data.get('price', 0)))
            quantity = int(item_data.get('quantity', 1))
            subtotal += price * quantity

        # Calculer le total avec les frais de livraison
        shipping_fee = validated_data.get('shipping_fee', Decimal('0'))
        if not isinstance(shipping_fee, Decimal):
            shipping_fee = Decimal(str(shipping_fee))
        total = subtotal + shipping_fee

        # Créer la commande avec le total calculé
        order = Order.objects.create(
            user=user,
            total=total,
            **validated_data
        )

        # Maintenant créer les items avec les informations du produit statique
        for item_data in items_data:
            quantity = int(item_data.get('quantity', 1))
            price = Decimal(str(item_data.get('price', 0)))

            # Support pour les produits DB (si product_id est fourni)
            product_id = item_data.get('product_id')
            product = None
            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                    # Réduire le stock si c'est un produit de la DB
                    if product.stock < quantity:
                        raise serializers.ValidationError(
                            f"Stock insuffisant pour {product.name}. Disponible: {product.stock}, Demandé: {quantity}"
                        )
                    product.stock -= quantity
                    product.save()
                except Product.DoesNotExist:
                    product = None

            # Créer l'OrderItem avec les infos du produit statique
            OrderItem.objects.create(
                order=order,
                product=product,  # Peut être None pour les produits statiques
                product_name=item_data.get('product_name', ''),
                product_image=item_data.get('product_image', ''),
                product_url=item_data.get('product_url', ''),
                product_description=item_data.get('product_description', ''),
                quantity=quantity,
                price=price
            )

        return order


class PaymentSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'payment_type', 'payment_method',
                  'status', 'transaction_id', 'created_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['order', 'amount', 'payment_type', 'payment_method']


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'product_external_id', 'product_name',
                  'product_image', 'product_url', 'rating', 'comment', 'status',
                  'is_approved', 'admin_reply', 'created_at', 'updated_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    # Allow product to be null for static products
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Review
        fields = ['product', 'product_external_id', 'product_name',
                  'product_image', 'product_url', 'rating', 'comment']

    def create(self, validated_data):
        # Auto-assign the current user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rating', 'comment', 'status', 'admin_reply']


class QuoteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteRequest
        fields = ['id', 'full_name', 'whatsapp', 'description', 'color',
                  'quantity', 'shoe_size', 'clothing_size', 'gender', 'photo',
                  'status', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuoteRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteRequest
        fields = ['full_name', 'whatsapp', 'description', 'color',
                  'quantity', 'shoe_size', 'clothing_size', 'gender', 'photo']


# Authentication Serializers
class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name',
                  'last_name', 'phone', 'address', 'postal_code', 'city', 'country']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            postal_code=validated_data.get('postal_code', ''),
            city=validated_data.get('city', ''),
            country=validated_data.get('country', 'Côte d\'Ivoire'),
            user_type='client'
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if not user:
                # Try to authenticate with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if not user:
                raise serializers.ValidationError('Identifiants invalides.')

            if not user.is_active:
                raise serializers.ValidationError('Ce compte a été désactivé.')

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Nom d\'utilisateur et mot de passe requis.')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with full details"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'phone', 'address', 'postal_code', 'city',
                  'country', 'custom_id', 'date_joined', 'is_staff']
        read_only_fields = ['id', 'custom_id', 'date_joined', 'user_type', 'is_staff']


class LogisticsRateSerializer(serializers.ModelSerializer):
    """Serializer for logistics shipping rates"""
    shipping_method_display = serializers.CharField(source='get_shipping_method_display', read_only=True)

    class Meta:
        model = LogisticsRate
        fields = [
            'id', 'shipping_method', 'shipping_method_display',
            'rate_per_kg', 'rate_per_m3', 'min_days', 'max_days',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate that appropriate rate field is provided"""
        shipping_method = data.get('shipping_method')

        # Aérien = rate_per_kg requis
        if shipping_method in ['air_rapide', 'air_express']:
            if not data.get('rate_per_kg'):
                raise serializers.ValidationError({
                    'rate_per_kg': 'Le tarif par kg est requis pour le transport aérien.'
                })

        # Maritime = rate_per_m3 requis
        if shipping_method in ['sea_no_motor', 'sea_with_motor']:
            if not data.get('rate_per_m3'):
                raise serializers.ValidationError({
                    'rate_per_m3': 'Le tarif par m³ est requis pour le transport maritime.'
                })

        # Vérifier que min_days < max_days
        if data.get('min_days') and data.get('max_days'):
            if data['min_days'] > data['max_days']:
                raise serializers.ValidationError({
                    'min_days': 'Le délai minimum doit être inférieur au délai maximum.'
                })

        return data


class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer for currency exchange rate"""

    class Meta:
        model = ExchangeRate
        fields = ['id', 'usd_to_fcfa', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
