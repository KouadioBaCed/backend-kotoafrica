#!/usr/bin/env python3
"""
Script pour corriger les permissions des endpoints logistics-rates
À exécuter sur le serveur de production avec : python fix_permissions.py
"""

import os
import sys

# Chemin du fichier à modifier
VIEWS_FILE = 'api/views.py'

# Vérifier que le fichier existe
if not os.path.exists(VIEWS_FILE):
    print(f"❌ Erreur : Le fichier {VIEWS_FILE} n'existe pas dans ce répertoire")
    print(f"   Répertoire actuel : {os.getcwd()}")
    sys.exit(1)

# Lire le contenu du fichier
with open(VIEWS_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Vérifier si les modifications sont déjà faites
if 'permission_classes=[AllowAny]' in content and 'all_rates' in content:
    print("✅ Les permissions sont déjà correctement configurées !")
    sys.exit(0)

# Rechercher et remplacer dans LogisticsRateViewSet
old_logistics_permissions = """    def get_permissions(self):
        """Allow read access to all authenticated users, but only admins can modify"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]  # Add admin check here if needed
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def all_rates(self, request):"""

new_logistics_permissions = """    def get_permissions(self):
        """Allow read access to all users, but only authenticated admins can modify"""
        if self.action in ['list', 'retrieve', 'all_rates']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]  # Only authenticated users can modify
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def all_rates(self, request):"""

# Rechercher et remplacer dans ExchangeRateViewSet
old_exchange_permissions = """    def get_permissions(self):
        """Allow read access to all authenticated users, but only admins can modify"""
        if self.action in ['list', 'retrieve', 'current']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]  # Add admin check here if needed
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def current(self, request):"""

new_exchange_permissions = """    def get_permissions(self):
        """Allow read access to all users, but only authenticated admins can modify"""
        if self.action in ['list', 'retrieve', 'current']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]  # Only authenticated users can modify
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def current(self, request):"""

# Faire les remplacements
modified = False

if old_logistics_permissions in content:
    content = content.replace(old_logistics_permissions, new_logistics_permissions)
    print("✅ Permissions LogisticsRateViewSet modifiées")
    modified = True
else:
    print("⚠️  LogisticsRateViewSet : Permissions déjà modifiées ou structure différente")

if old_exchange_permissions in content:
    content = content.replace(old_exchange_permissions, new_exchange_permissions)
    print("✅ Permissions ExchangeRateViewSet modifiées")
    modified = True
else:
    print("⚠️  ExchangeRateViewSet : Permissions déjà modifiées ou structure différente")

if not modified:
    print("\n❌ Aucune modification n'a été effectuée.")
    print("   Le fichier a peut-être déjà été modifié ou la structure est différente.")
    sys.exit(1)

# Créer une sauvegarde
backup_file = VIEWS_FILE + '.backup'
with open(backup_file, 'w', encoding='utf-8') as f:
    # Lire le fichier original
    with open(VIEWS_FILE, 'r', encoding='utf-8') as original:
        f.write(original.read())
print(f"💾 Sauvegarde créée : {backup_file}")

# Écrire le nouveau contenu
with open(VIEWS_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Fichier modifié avec succès !")
print("\n📝 Prochaines étapes :")
print("   1. Redémarrer le serveur Django/Gunicorn :")
print("      sudo systemctl restart gunicorn")
print("   2. Vérifier que l'API fonctionne :")
print("      curl https://api.kotoafrica.com/api/logistics-rates/all_rates/")
print("\n   Si quelque chose ne va pas, restaurez la sauvegarde :")
print(f"      cp {backup_file} {VIEWS_FILE}")
