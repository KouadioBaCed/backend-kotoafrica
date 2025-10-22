"""
ASGI config for koto_africa project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'koto_africa.settings')

application = get_asgi_application()
