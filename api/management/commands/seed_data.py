from django.core.management.base import BaseCommand
from api.models import User, Supplier, Category, Product, Order, OrderItem, Payment, Review
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed database with demo data for KÔTO AFRICA'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        # Create Categories
        categories_data = [
            {'name': 'Artisanat', 'slug': 'artisanat', 'description': 'Produits artisanaux africains'},
            {'name': 'Textile', 'slug': 'textile', 'description': 'Tissus et textiles'},
            {'name': 'Électronique', 'slug': 'electronique', 'description': 'Appareils électroniques'},
            {'name': 'Mode', 'slug': 'mode', 'description': 'Vêtements et accessoires'},
            {'name': 'Décoration', 'slug': 'decoration', 'description': 'Articles de décoration'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={'name': cat_data['name'], 'description': cat_data['description']}
            )
            categories[cat_data['slug']] = cat
            if created:
                self.stdout.write(f'Created category: {cat.name}')

        # Create Users (Suppliers)
        suppliers_users_data = [
            {
                'username': 'artisanat_ivoirien',
                'email': 'contact@artisanat-ci.com',
                'password': 'password123',
                'user_type': 'african_supplier',
                'first_name': 'Artisanat',
                'last_name': 'Ivoirien',
            },
            {
                'username': 'ghana_textiles',
                'email': 'info@ghana-textiles.com',
                'password': 'password123',
                'user_type': 'african_supplier',
                'first_name': 'Ghana',
                'last_name': 'Textiles',
            },
            {
                'username': 'asian_electronics',
                'email': 'sales@asian-electronics.com',
                'password': 'password123',
                'user_type': 'asian_supplier',
                'first_name': 'Asian',
                'last_name': 'Electronics',
            },
            {
                'username': 'senegal_fashion',
                'email': 'contact@senegal-fashion.com',
                'password': 'password123',
                'user_type': 'african_supplier',
                'first_name': 'Senegal',
                'last_name': 'Fashion',
            },
        ]

        suppliers_users = []
        for user_data in suppliers_users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'user_type': user_data['user_type'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'Created user: {user.username}')
            suppliers_users.append(user)

        # Create Suppliers
        suppliers_data = [
            {
                'user': suppliers_users[0],
                'supplier_type': 'african',
                'company_name': 'Artisanat Ivoirien',
                'country': 'Côte d\'Ivoire',
                'rating': 4.8,
                'products_count': 0,
                'verified': True,
            },
            {
                'user': suppliers_users[1],
                'supplier_type': 'african',
                'company_name': 'Ghana Textiles',
                'country': 'Ghana',
                'rating': 4.6,
                'products_count': 0,
                'verified': True,
            },
            {
                'user': suppliers_users[2],
                'supplier_type': 'asian',
                'company_name': 'Asian Electronics Co.',
                'country': 'Chine',
                'rating': 4.5,
                'products_count': 0,
                'verified': True,
            },
            {
                'user': suppliers_users[3],
                'supplier_type': 'african',
                'company_name': 'Senegal Fashion',
                'country': 'Sénégal',
                'rating': 4.7,
                'products_count': 0,
                'verified': True,
            },
        ]

        suppliers = []
        for sup_data in suppliers_data:
            sup, created = Supplier.objects.get_or_create(
                user=sup_data['user'],
                defaults=sup_data
            )
            suppliers.append(sup)
            if created:
                self.stdout.write(f'Created supplier: {sup.company_name}')

        # Create Products
        products_data = [
            {
                'supplier': suppliers[0],
                'category': categories['artisanat'],
                'name': 'Masque Baoulé Traditionnel',
                'description': 'Masque africain artisanal sculpté à la main par des artisans ivoiriens. Pièce unique représentant la culture Baoulé.',
                'price': 45000,
                'origin': 'africa',
                'country': 'Côte d\'Ivoire',
                'stock': 15,
                'rating': 4.8,
                'reviews_count': 23,
                'delivery_time': 7,
            },
            {
                'supplier': suppliers[1],
                'category': categories['textile'],
                'name': 'Tissu Wax Premium',
                'description': 'Tissu africain en coton imprimé wax. Motifs traditionnels colorés. 6 yards.',
                'price': 12000,
                'origin': 'africa',
                'country': 'Ghana',
                'stock': 50,
                'rating': 4.9,
                'reviews_count': 67,
                'delivery_time': 5,
            },
            {
                'supplier': suppliers[2],
                'category': categories['electronique'],
                'name': 'Smartphone Android 12',
                'description': 'Smartphone dernière génération avec écran AMOLED 6.5", 128GB stockage, appareil photo 48MP.',
                'price': 85000,
                'origin': 'asia',
                'country': 'Chine',
                'stock': 200,
                'rating': 4.4,
                'reviews_count': 156,
                'delivery_time': 14,
            },
            {
                'supplier': suppliers[3],
                'category': categories['mode'],
                'name': 'Robe Africaine Bazin',
                'description': 'Robe élégante en bazin riche brodé. Confection artisanale, disponible en plusieurs tailles.',
                'price': 35000,
                'origin': 'africa',
                'country': 'Sénégal',
                'stock': 25,
                'rating': 4.7,
                'reviews_count': 34,
                'delivery_time': 6,
            },
            {
                'supplier': suppliers[2],
                'category': categories['electronique'],
                'name': 'Écouteurs Bluetooth TWS',
                'description': 'Écouteurs sans fil avec réduction de bruit active, autonomie 24h avec boîtier de charge.',
                'price': 15000,
                'origin': 'asia',
                'country': 'Chine',
                'stock': 150,
                'rating': 4.3,
                'reviews_count': 89,
                'delivery_time': 12,
            },
            {
                'supplier': suppliers[1],
                'category': categories['decoration'],
                'name': 'Panier Artisanal Bolga',
                'description': 'Panier tissé à la main en fibres naturelles. Design coloré traditionnel du Ghana.',
                'price': 8000,
                'origin': 'africa',
                'country': 'Ghana',
                'stock': 40,
                'rating': 4.6,
                'reviews_count': 45,
                'delivery_time': 5,
            },
            {
                'supplier': suppliers[0],
                'category': categories['artisanat'],
                'name': 'Statue en Bois d\'Ébène',
                'description': 'Sculpture artisanale en bois d\'ébène représentant une figure traditionnelle africaine. Hauteur 30cm.',
                'price': 55000,
                'origin': 'africa',
                'country': 'Côte d\'Ivoire',
                'stock': 10,
                'rating': 4.9,
                'reviews_count': 12,
                'delivery_time': 8,
            },
            {
                'supplier': suppliers[3],
                'category': categories['mode'],
                'name': 'Boubou Brodé Homme',
                'description': 'Boubou traditionnel brodé à la main. Tissu en coton premium, motifs élégants.',
                'price': 42000,
                'origin': 'africa',
                'country': 'Sénégal',
                'stock': 18,
                'rating': 4.6,
                'reviews_count': 28,
                'delivery_time': 7,
            },
            {
                'supplier': suppliers[2],
                'category': categories['electronique'],
                'name': 'Montre Connectée Smart',
                'description': 'Montre intelligente avec suivi santé, notifications, étanche IP68. Autonomie 7 jours.',
                'price': 25000,
                'origin': 'asia',
                'country': 'Chine',
                'stock': 80,
                'rating': 4.5,
                'reviews_count': 142,
                'delivery_time': 10,
            },
            {
                'supplier': suppliers[1],
                'category': categories['textile'],
                'name': 'Pagne Kente Authentique',
                'description': 'Pagne Kente tissé traditionnellement. Couleurs vives, motifs symboliques ghanéens.',
                'price': 28000,
                'origin': 'africa',
                'country': 'Ghana',
                'stock': 30,
                'rating': 4.8,
                'reviews_count': 52,
                'delivery_time': 6,
            },
            {
                'supplier': suppliers[0],
                'category': categories['decoration'],
                'name': 'Tableau Batik Africain',
                'description': 'Tableau décoratif en batik fait main. Scènes de vie africaine, dimensions 60x80cm.',
                'price': 38000,
                'origin': 'africa',
                'country': 'Côte d\'Ivoire',
                'stock': 12,
                'rating': 4.7,
                'reviews_count': 19,
                'delivery_time': 9,
            },
            {
                'supplier': suppliers[2],
                'category': categories['electronique'],
                'name': 'Tablette Android 10 pouces',
                'description': 'Tablette tactile 10", 64GB, processeur Octa-core, idéale pour multimédia et productivité.',
                'price': 65000,
                'origin': 'asia',
                'country': 'Chine',
                'stock': 45,
                'rating': 4.4,
                'reviews_count': 73,
                'delivery_time': 12,
            },
        ]

        products = []
        for prod_data in products_data:
            prod, created = Product.objects.get_or_create(
                name=prod_data['name'],
                supplier=prod_data['supplier'],
                defaults=prod_data
            )
            products.append(prod)
            if created:
                self.stdout.write(f'Created product: {prod.name}')

        # Update suppliers products count
        for supplier in suppliers:
            supplier.products_count = Product.objects.filter(supplier=supplier).count()
            supplier.save()

        # Create a client user
        client, created = User.objects.get_or_create(
            username='client_test',
            defaults={
                'email': 'client@test.com',
                'user_type': 'client',
                'first_name': 'Kouassi',
                'last_name': 'Yao',
                'phone': '+225 07 XX XX XX XX',
                'address': 'Cocody Angré, Abidjan',
                'postal_code': '01',
                'city': 'Abidjan',
                'country': 'Côte d\'Ivoire',
            }
        )
        if created:
            client.set_password('password123')
            client.save()
            self.stdout.write(f'Created client: {client.username}')

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write(f'Created {Category.objects.count()} categories')
        self.stdout.write(f'Created {Supplier.objects.count()} suppliers')
        self.stdout.write(f'Created {Product.objects.count()} products')
