# KÔTO AFRICA - Backend API

Backend Django REST Framework pour la plateforme d'intermédiation e-commerce KÔTO AFRICA.

## Installation

1. Créer un environnement virtuel :
```bash
python -m venv venv
```

2. Activer l'environnement virtuel :
- Windows : `venv\Scripts\activate`
- Linux/Mac : `source venv/bin/activate`

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Effectuer les migrations :
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Importer les produits depuis Excel** (Recommandé) :
```bash
# Créer les fichiers Excel exemples
python create_excel_samples.py

# Importer les produits
python manage.py import_products_excel
```

6. Créer un superutilisateur :
```bash
python manage.py createsuperuser
```

7. Lancer le serveur :
```bash
python manage.py runserver
```

## 📊 Import de Produits depuis Excel

KÔTO AFRICA utilise des fichiers Excel pour gérer les produits par catégorie.

### Démarrage Rapide

```bash
# 1. Créer les fichiers Excel exemples (25 produits)
python create_excel_samples.py

# 2. Importer les produits
python manage.py import_products_excel
```

**Fichiers créés** :
- `data/products_excel/artisanat.xlsx` (5 produits)
- `data/products_excel/textile.xlsx` (5 produits)
- `data/products_excel/electronique.xlsx` (5 produits)
- `data/products_excel/mode.xlsx` (5 produits)
- `data/products_excel/decoration.xlsx` (5 produits)

### Format Excel Requis

Chaque fichier doit contenir ces colonnes :
- `nom`, `description`, `prix`, `origine`, `pays`, `stock`, `delai_livraison`, `fournisseur`, `categorie`

📖 **Documentation complète** : Voir [IMPORT_EXCEL.md](IMPORT_EXCEL.md)

## Endpoints API

### Users
- `GET /api/users/` - Liste des utilisateurs
- `POST /api/users/` - Créer un utilisateur
- `GET /api/users/{id}/` - Détails d'un utilisateur
- `PUT /api/users/{id}/` - Modifier un utilisateur
- `DELETE /api/users/{id}/` - Supprimer un utilisateur

### Suppliers
- `GET /api/suppliers/` - Liste des fournisseurs
- `POST /api/suppliers/` - Créer un fournisseur
- `GET /api/suppliers/{id}/` - Détails d'un fournisseur

### Categories
- `GET /api/categories/` - Liste des catégories
- `POST /api/categories/` - Créer une catégorie

### Products
- `GET /api/products/` - Liste des produits
- `GET /api/products/popular/` - Produits populaires
- `GET /api/products/featured/` - Produits vedettes
- `POST /api/products/` - Créer un produit
- `GET /api/products/{id}/` - Détails d'un produit
- `PUT /api/products/{id}/` - Modifier un produit

Filtres disponibles :
- `?origin=africa` ou `?origin=asia`
- `?category=1`
- `?supplier=1`
- `?search=masque`
- `?ordering=-price` (tri par prix décroissant)

### Orders
- `GET /api/orders/` - Liste des commandes
- `POST /api/orders/` - Créer une commande
- `GET /api/orders/{id}/` - Détails d'une commande
- `POST /api/orders/{id}/update_status/` - Mettre à jour le statut

### Payments
- `GET /api/payments/` - Liste des paiements
- `POST /api/payments/` - Créer un paiement
- `GET /api/payments/{id}/` - Détails d'un paiement

### Reviews
- `GET /api/reviews/` - Liste des avis
- `POST /api/reviews/` - Créer un avis
- `POST /api/reviews/{id}/approve/` - Approuver un avis

## Modèles

### User
Modèle utilisateur étendu avec support pour :
- Clients (ID auto-généré : KA-[code postal]-[numéro])
- Fournisseurs africains
- Fournisseurs asiatiques
- Administrateurs

### Supplier
Profil fournisseur avec :
- Type (africain/asiatique)
- Informations entreprise
- Rating et vérification
- API key pour fournisseurs asiatiques

### Product
Produits avec :
- Origine (Afrique/Asie)
- Prix, stock, délai livraison
- Rating et nombre d'avis
- Images multiples

### Order
Commandes avec :
- Statut (pending, confirmed, shipped, delivered, cancelled)
- Statut paiement (pending, partial, completed)
- Numéro de suivi auto-généré

### Payment
Paiements avec :
- Type (acompte 50% / solde)
- Méthode (Mobile Money, Carte, Espèces)

### Review
Avis produits avec :
- Note 1-5 étoiles
- Commentaire
- Approbation admin

## Administration

Accès à l'interface admin Django : http://localhost:8001/admin

Toutes les entités sont gérables via l'admin avec :
- Filtres avancés
- Recherche
- Actions groupées
