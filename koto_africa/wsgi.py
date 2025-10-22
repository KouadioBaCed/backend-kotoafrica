"""
WSGI config for koto_africa project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'koto_africa.settings')

application = get_wsgi_application()
