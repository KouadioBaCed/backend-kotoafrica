"""
URL configuration for koto_africa project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import HttpResponse
import os


def serve_media_with_cors(request, path, document_root=None):
    """
    Serve media files with CORS headers to allow cross-origin access for PDF generation
    """
    response = serve(request, path, document_root=document_root)

    # Add CORS headers for media files
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Origin, Content-Type, Accept'
    response['Cross-Origin-Resource-Policy'] = 'cross-origin'

    return response


def product_share_view(request, product_id):
    """
    Serves an HTML page with Open Graph meta tags for product link previews.
    Social media crawlers (WhatsApp, Facebook, Twitter) read these tags to
    generate rich link previews with product image, title, and description.
    Normal users are redirected to the SPA product page via JavaScript.
    """
    from api.models import Product, ProductImage

    # Frontend URL (from env or default)
    frontend_url = os.getenv('FRONTEND_URL', 'https://kotoafrica.com')
    spa_url = f"{frontend_url}/produit/{product_id}"

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        # Redirect to SPA even if product not found (SPA will handle 404)
        return HttpResponse(
            f'<html><head><meta http-equiv="refresh" content="0;url={spa_url}"></head></html>',
            content_type='text/html'
        )

    # Get product image (primary first, then any image)
    backend_url = os.getenv('BACKEND_URL', request.build_absolute_uri('/').rstrip('/'))
    image_url = ''
    primary_image = product.images.filter(is_primary=True).first()
    if not primary_image:
        primary_image = product.images.first()
    if primary_image and primary_image.image:
        img_path = primary_image.image.url
        if img_path.startswith('http'):
            image_url = img_path
        else:
            image_url = f"{backend_url}{img_path}"

    # Build description
    price_display = ''
    if product.price_fcfa:
        price_display = f"{int(product.price_fcfa):,} FCFA".replace(',', ' ')
    elif product.price:
        price_display = f"{int(product.price):,} FCFA".replace(',', ' ')

    description = product.description[:200] if product.description else ''
    if price_display:
        description = f"{price_display} - {description}"

    # Escape HTML
    from html import escape
    title = escape(product.name or 'Produit')
    description = escape(description)
    site_name = 'KOTO AFRICA'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {site_name}</title>

    <!-- Open Graph / Facebook / WhatsApp -->
    <meta property="og:type" content="product">
    <meta property="og:url" content="{spa_url}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:site_name" content="{site_name}">
    <meta property="og:image" content="{image_url}">
    <meta property="og:image:width" content="600">
    <meta property="og:image:height" content="600">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{image_url}">

    <!-- Redirect to SPA -->
    <meta http-equiv="refresh" content="0;url={spa_url}">
</head>
<body>
    <p>Redirection vers <a href="{spa_url}">{title}</a>...</p>
    <script>window.location.replace("{spa_url}");</script>
</body>
</html>"""

    return HttpResponse(html, content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('share/product/<int:product_id>/', product_share_view, name='product_share'),
]

# Serve media files with CORS headers (works in both DEBUG and production)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media_with_cors, {'document_root': settings.MEDIA_ROOT}),
]

# Also add static files serving in debug mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
