Backend environment setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS`.
3. Restart the Django development server.

This project uses python-dotenv to load `backend/.env` automatically from `settings.py`.
