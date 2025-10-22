from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Supplier, Category, Product, ProductImage,
    Order, OrderItem, Payment, Review, QuoteRequest
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'phone', 'address', 'postal_code', 'city',
                  'country', 'custom_id', 'date_joined']
        read_only_fields = ['id', 'custom_id', 'date_joined']


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
        fields = ['id', 'product', 'quantity', 'price']


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
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        total = 0
        for item_data in items_data:
            product = Product.objects.get(id=item_data['product_id'])
            quantity = item_data['quantity']
            price = product.price

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price
            )
            total += price * quantity

        order.total = total + order.shipping_fee
        order.save()

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
        fields = ['id', 'user', 'product', 'rating', 'comment', 'status',
                  'is_approved', 'admin_reply', 'created_at', 'updated_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['product', 'rating', 'comment']


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
