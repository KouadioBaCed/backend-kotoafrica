from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Supplier, Category, Provenance, Product, ProductImage,
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
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'products_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_products_count(self, obj):
        return obj.products.count()


class ProvenanceSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Provenance
        fields = ['id', 'name', 'slug', 'description', 'products_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_products_count(self, obj):
        return obj.products.count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary']


class ProductSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    origin = ProvenanceSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Product
        fields = ['id', 'supplier', 'category', 'name', 'description', 'price',
                  'price_fcfa', 'old_price', 'old_price_fcfa',
                  'marketing_price_fcfa', 'origin', 'country', 'stock', 'rating',
                  'reviews_count', 'delivery_time', 'status', 'status_display',
                  'is_active', 'video', 'created_at', 'updated_at', 'images',
                  'order_count']


class ProductCreateSerializer(serializers.ModelSerializer):
    origin = serializers.PrimaryKeyRelatedField(queryset=Provenance.objects.all(), required=False, allow_null=True)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Product
        fields = ['id', 'category', 'name', 'description', 'price', 'price_fcfa',
                  'old_price', 'old_price_fcfa',
                  'marketing_price_fcfa', 'origin', 'country', 'stock',
                  'delivery_time', 'status', 'supplier', 'video']
        read_only_fields = ['id']

    def validate(self, data):
        if data.get('status') == 'promotion':
            old_price = data.get('old_price')
            price = data.get('price')
            if old_price is None:
                raise serializers.ValidationError({
                    'old_price': "L'ancien prix est requis pour un produit en promotion."
                })
            if price is not None and old_price <= price:
                raise serializers.ValidationError({
                    'old_price': "L'ancien prix doit être supérieur au prix actuel."
                })
            old_price_fcfa = data.get('old_price_fcfa')
            price_fcfa = data.get('price_fcfa')
            if old_price_fcfa is not None and price_fcfa is not None and old_price_fcfa <= price_fcfa:
                raise serializers.ValidationError({
                    'old_price_fcfa': "L'ancien prix FCFA doit être supérieur au prix actuel FCFA."
                })
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'product_url',
                  'product_description', 'quantity', 'price', 'size', 'color', 'delivery_mode']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    balance_payment_initiated = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'tracking_number', 'status', 'payment_status',
                  'payment_mode', 'shipping_method', 'total', 'amount_due',
                  'paid_amount', 'shipping_address', 'shipping_fee', 'service_fee',
                  'admin_notes', 'created_at', 'updated_at', 'items',
                  'balance_payment_initiated']

    def get_balance_payment_initiated(self, obj):
        """Vérifie s'il y a un paiement de solde en attente (client a initié via Wave)"""
        return obj.payments.filter(payment_type='balance', status='pending').exists()


class OrderCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(child=serializers.DictField(), write_only=True)
    payment_mode = serializers.ChoiceField(choices=['partial', 'total'], default='total')

    class Meta:
        model = Order
        fields = ['shipping_address', 'payment_mode', 'items']

    def create(self, validated_data):
        from decimal import Decimal
        import logging
        logger = logging.getLogger(__name__)

        items_data = validated_data.pop('items')
        payment_mode = validated_data.pop('payment_mode', 'total')

        request = self.context.get('request')
        user = request.user if request else None

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Utilisateur non authentifié")

        logger.info(f'OrderCreate - user: {user.username} (ID: {user.id}), payment_mode: {payment_mode}')

        # Calculer le total en FCFA
        subtotal = Decimal('0')
        delivery_modes = set()
        for item_data in items_data:
            price = Decimal(str(item_data.get('price', 0)))
            quantity = int(item_data.get('quantity', 1))
            subtotal += price * quantity
            delivery_modes.add(item_data.get('delivery_mode', 'bateau'))

        # Déterminer le shipping_method global
        if len(delivery_modes) == 1:
            shipping_method = delivery_modes.pop()
        else:
            shipping_method = 'mixte'

        # Calculer le montant à payer
        total = subtotal
        if payment_mode == 'partial':
            amount_due = round(total * Decimal('0.7'))
        else:
            amount_due = total

        # Créer la commande
        order = Order.objects.create(
            user=user,
            total=total,
            amount_due=amount_due,
            service_fee=Decimal('0'),
            payment_mode=payment_mode,
            shipping_method=shipping_method,
            shipping_address=validated_data.get('shipping_address', ''),
        )

        logger.info(f'Order #{order.tracking_number} créée - total: {total} FCFA, à payer: {amount_due} FCFA')

        # Créer les items
        for item_data in items_data:
            quantity = int(item_data.get('quantity', 1))
            price = Decimal(str(item_data.get('price', 0)))
            delivery_mode = item_data.get('delivery_mode', 'bateau')

            product_id = item_data.get('product_id')
            product = None
            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                    if product.stock < quantity:
                        raise serializers.ValidationError(
                            f"Stock insuffisant pour {product.name}. Disponible: {product.stock}, Demandé: {quantity}"
                        )
                    product.stock -= quantity
                    product.save()
                except Product.DoesNotExist:
                    product = None

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=item_data.get('product_name', ''),
                product_image=item_data.get('product_image', ''),
                product_url=item_data.get('product_url', ''),
                product_description=item_data.get('product_description', ''),
                quantity=quantity,
                price=price,
                size=item_data.get('size', ''),
                color=item_data.get('color', ''),
                delivery_mode=delivery_mode,
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
                  'status', 'notes', 'user', 'quoted_price', 'payment_status', 'order',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'payment_status', 'order']


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
