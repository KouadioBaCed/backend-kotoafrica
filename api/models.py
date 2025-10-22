from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """Extended User model for clients and suppliers"""
    USER_TYPE_CHOICES = [
        ('client', 'Client'),
        ('african_supplier', 'Fournisseur Africain'),
        ('asian_supplier', 'Fournisseur Asiatique'),
        ('admin', 'Administrateur'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Côte d\'Ivoire')
    custom_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Fix for groups and user_permissions reverse accessor conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

    class Meta:
        db_table = 'users'

    def save(self, *args, **kwargs):
        # Generate custom_id for clients (KA-[postal_code]-[number])
        if self.user_type == 'client' and not self.custom_id:
            count = User.objects.filter(postal_code=self.postal_code, user_type='client').count()
            self.custom_id = f"KA-{self.postal_code}-{str(count + 1).zfill(4)}"
        super().save(*args, **kwargs)


class Supplier(models.Model):
    """Supplier profile (African or Asian)"""
    SUPPLIER_TYPE_CHOICES = [
        ('african', 'Africain'),
        ('asian', 'Asiatique'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supplier_profile')
    supplier_type = models.CharField(max_length=10, choices=SUPPLIER_TYPE_CHOICES)
    company_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    products_count = models.IntegerField(default=0)
    verified = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, blank=True, null=True)  # For Asian suppliers
    last_sync = models.DateTimeField(blank=True, null=True)  # For Asian suppliers

    class Meta:
        db_table = 'suppliers'

    def __str__(self):
        return self.company_name


class Category(models.Model):
    """Product categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model"""
    ORIGIN_CHOICES = [
        ('africa', 'Afrique'),
        ('asia', 'Asie'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    country = models.CharField(max_length=100)
    stock = models.IntegerField(validators=[MinValueValidator(0)])
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    reviews_count = models.IntegerField(default=0)
    delivery_time = models.IntegerField(help_text='Délai de livraison en jours')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'

    def __str__(self):
        return f"Image for {self.product.name}"


class Order(models.Model):
    """Order model"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('partial', 'Partiel'),
        ('completed', 'Complet'),
    ]

    SHIPPING_METHOD_CHOICES = [
        ('air_rapide', 'Aérien Rapide'),
        ('air_express', 'Aérien Express'),
        ('sea_no_motor', 'Maritime sans Moteur'),
        ('sea_with_motor', 'Maritime avec Moteur'),
        ('local', 'Livraison Locale'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    tracking_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    shipping_method = models.CharField(max_length=20, choices=SHIPPING_METHOD_CHOICES, default='local')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.TextField()
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return self.tracking_number

    def save(self, *args, **kwargs):
        # Generate tracking number
        if not self.tracking_number:
            from django.utils import timezone
            year = timezone.now().year
            count = Order.objects.filter(created_at__year=year).count()
            self.tracking_number = f"KA-{year}-{str(count + 1).zfill(3)}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Order items"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class Payment(models.Model):
    """Payment model"""
    PAYMENT_TYPE_CHOICES = [
        ('deposit', 'Acompte'),
        ('balance', 'Solde'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte Bancaire'),
        ('cash', 'Espèces'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.amount} FCFA"


class Review(models.Model):
    """Product reviews"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_approved = models.BooleanField(default=False)  # Kept for backward compatibility
    admin_reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        unique_together = ['user', 'product']

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

    def save(self, *args, **kwargs):
        # Sync is_approved with status for backward compatibility
        if self.status == 'approved':
            self.is_approved = True
        else:
            self.is_approved = False
        super().save(*args, **kwargs)


class QuoteRequest(models.Model):
    """Quote request from clients"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('quoted', 'Devis envoyé'),
        ('accepted', 'Accepté'),
        ('rejected', 'Rejeté'),
    ]

    GENDER_CHOICES = [
        ('homme', 'Homme'),
        ('femme', 'Femme'),
        ('enfant', 'Enfant'),
    ]

    full_name = models.CharField(max_length=255)
    whatsapp = models.CharField(max_length=20)
    description = models.TextField()
    color = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    shoe_size = models.CharField(max_length=10, blank=True)
    clothing_size = models.CharField(max_length=10, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    photo = models.ImageField(upload_to='quote_requests/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quote_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Quote request from {self.full_name} - {self.description[:50]}"
