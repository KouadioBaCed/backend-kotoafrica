from django.contrib import admin
from .models import (
    User, Supplier, Category, Product, ProductImage,
    Order, OrderItem, Payment, Review, QuoteRequest,
    LogisticsRate, ExchangeRate
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'custom_id', 'date_joined']
    list_filter = ['user_type', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'custom_id']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'supplier_type', 'country', 'rating', 'verified']
    list_filter = ['supplier_type', 'verified', 'country']
    search_fields = ['company_name', 'country']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier', 'category', 'price', 'stock', 'origin', 'is_active']
    list_filter = ['origin', 'category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'country']
    inlines = [ProductImageInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'user', 'status', 'payment_status', 'shipping_method', 'total', 'created_at']
    list_filter = ['status', 'payment_status', 'shipping_method', 'created_at']
    search_fields = ['tracking_number', 'user__username']
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'payment_type', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'status', 'created_at']
    search_fields = ['transaction_id', 'order__tracking_number']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'status', 'is_approved', 'created_at']
    list_filter = ['rating', 'status', 'is_approved', 'created_at']
    search_fields = ['comment', 'user__username', 'product__name']


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'whatsapp', 'gender', 'quantity', 'status', 'created_at']
    list_filter = ['status', 'gender', 'created_at']
    search_fields = ['full_name', 'whatsapp', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LogisticsRate)
class LogisticsRateAdmin(admin.ModelAdmin):
    list_display = ['shipping_method', 'rate_per_kg', 'rate_per_m3', 'min_days', 'max_days', 'is_active', 'updated_at']
    list_filter = ['shipping_method', 'is_active']
    search_fields = ['shipping_method']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['shipping_method']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['usd_to_fcfa', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def save_model(self, request, obj, form, change):
        """Automatically deactivate other rates when creating a new active one"""
        if obj.is_active:
            ExchangeRate.objects.filter(is_active=True).update(is_active=False)
        super().save_model(request, obj, form, change)
