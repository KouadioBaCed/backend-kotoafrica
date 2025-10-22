from django.core.management.base import BaseCommand
from api.models import User, Supplier, Category, Product
import pandas as pd
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Import products from Excel files by category'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting product import from Excel files...')

        # Créer les catégories d'abord
        categories_data = {
            'artisanat': {'name': 'Artisanat', 'slug': 'artisanat', 'description': 'Produits artisanaux africains'},
            'textile': {'name': 'Textile', 'slug': 'textile', 'description': 'Tissus et textiles'},
            'electronique': {'name': 'Électronique', 'slug': 'electronique', 'description': 'Appareils électroniques'},
            'mode': {'name': 'Mode', 'slug': 'mode', 'description': 'Vêtements et accessoires'},
            'decoration': {'name': 'Décoration', 'slug': 'decoration', 'description': 'Articles de décoration'},
        }

        categories = {}
        for slug, cat_data in categories_data.items():
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': cat_data['name'], 'description': cat_data['description']}
            )
            categories[slug] = cat
            if created:
                self.stdout.write(f'  ✅ Catégorie créée: {cat.name}')

        # Créer les fournisseurs
        suppliers_data = [
            {
                'username': 'artisanat_ivoirien',
                'email': 'contact@artisanat-ci.com',
                'user_type': 'african_supplier',
                'company_name': 'Artisanat Ivoirien',
                'country': 'Côte d\'Ivoire',
                'supplier_type': 'african',
            },
            {
                'username': 'ghana_textiles',
                'email': 'info@ghana-textiles.com',
                'user_type': 'african_supplier',
                'company_name': 'Ghana Textiles',
                'country': 'Ghana',
                'supplier_type': 'african',
            },
            {
                'username': 'asian_electronics',
                'email': 'sales@asian-electronics.com',
                'user_type': 'asian_supplier',
                'company_name': 'Asian Electronics Co.',
                'country': 'Chine',
                'supplier_type': 'asian',
            },
            {
                'username': 'senegal_fashion',
                'email': 'contact@senegal-fashion.com',
                'user_type': 'african_supplier',
                'company_name': 'Senegal Fashion',
                'country': 'Sénégal',
                'supplier_type': 'african',
            },
        ]

        suppliers = {}
        for sup_data in suppliers_data:
            # Créer ou récupérer l'utilisateur
            user, user_created = User.objects.get_or_create(
                username=sup_data['username'],
                defaults={
                    'email': sup_data['email'],
                    'user_type': sup_data['user_type'],
                }
            )
            if user_created:
                user.set_password('password123')
                user.save()

            # Créer ou récupérer le fournisseur
            supplier, created = Supplier.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': sup_data['company_name'],
                    'country': sup_data['country'],
                    'supplier_type': sup_data['supplier_type'],
                    'verified': True,
                    'rating': 4.5,
                }
            )
            suppliers[sup_data['company_name']] = supplier
            if created:
                self.stdout.write(f'  ✅ Fournisseur créé: {supplier.company_name}')

        # Chemin vers les fichiers Excel
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        excel_dir = base_dir / 'data' / 'products_excel'

        if not excel_dir.exists():
            self.stdout.write(self.style.ERROR(f'Le dossier {excel_dir} n\'existe pas!'))
            self.stdout.write('Veuillez d\'abord créer les fichiers Excel avec: python create_excel_samples.py')
            return

        # Lire et importer chaque fichier Excel
        excel_files = list(excel_dir.glob('*.xlsx'))

        if not excel_files:
            self.stdout.write(self.style.ERROR('Aucun fichier Excel trouvé!'))
            self.stdout.write('Veuillez d\'abord créer les fichiers Excel avec: python create_excel_samples.py')
            return

        total_products = 0

        for excel_file in excel_files:
            self.stdout.write(f'\n📂 Lecture de {excel_file.name}...')

            try:
                df = pd.read_excel(excel_file, engine='openpyxl')

                # Vérifier les colonnes requises
                required_columns = ['nom', 'description', 'prix', 'origine', 'pays', 'stock', 'delai_livraison', 'fournisseur', 'categorie']
                missing_columns = [col for col in required_columns if col not in df.columns]

                if missing_columns:
                    self.stdout.write(self.style.ERROR(f'  ❌ Colonnes manquantes: {", ".join(missing_columns)}'))
                    continue

                # Importer chaque produit
                for _, row in df.iterrows():
                    # Récupérer le fournisseur
                    supplier = suppliers.get(row['fournisseur'])
                    if not supplier:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  Fournisseur non trouvé: {row["fournisseur"]}'))
                        continue

                    # Récupérer la catégorie
                    category_slug = row['categorie'].lower().replace('é', 'e').replace('è', 'e')
                    category = categories.get(category_slug)
                    if not category:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  Catégorie non trouvée: {row["categorie"]}'))
                        continue

                    # Créer ou mettre à jour le produit
                    product, created = Product.objects.update_or_create(
                        name=row['nom'],
                        supplier=supplier,
                        defaults={
                            'category': category,
                            'description': row['description'],
                            'price': float(row['prix']),
                            'origin': row['origine'],
                            'country': row['pays'],
                            'stock': int(row['stock']),
                            'delivery_time': int(row['delai_livraison']),
                            'is_active': True,
                            'rating': 4.5,  # Rating par défaut
                            'reviews_count': 0,
                        }
                    )

                    if created:
                        total_products += 1
                        self.stdout.write(f'  ✅ Produit créé: {product.name}')
                    else:
                        self.stdout.write(f'  ♻️  Produit mis à jour: {product.name}')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Erreur lors de la lecture de {excel_file.name}: {str(e)}'))

        # Mettre à jour le compteur de produits pour chaque fournisseur
        for supplier in suppliers.values():
            supplier.products_count = Product.objects.filter(supplier=supplier).count()
            supplier.save()

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Import terminé avec succès!'))
        self.stdout.write(f'Total produits créés: {total_products}')
        self.stdout.write(f'Total produits en base: {Product.objects.count()}')
