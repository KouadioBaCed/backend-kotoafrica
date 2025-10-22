# 🚀 Démarrage Rapide - Backend KÔTO AFRICA

Guide simplifié pour démarrer le backend avec des produits depuis Excel.

## 📋 Prérequis

- Python 3.10+
- pip

## ⚡ Installation en 5 Minutes

### 1️⃣ Créer l'environnement virtuel

**Windows :**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac :**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3️⃣ Créer la base de données

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4️⃣ Créer et importer les produits Excel

```bash
# Créer les fichiers Excel avec 25 produits exemples
python create_excel_samples.py

# Importer les produits dans la base de données
python manage.py import_products_excel
```

### 5️⃣ Créer un compte administrateur

```bash
python manage.py createsuperuser
```

Suivez les instructions :
- Username : `admin`
- Email : `admin@kotoafrica.com`
- Password : `admin123` (ou votre choix)

### 6️⃣ Lancer le serveur

```bash
python manage.py runserver
```

## ✅ Vérification

Le serveur démarre sur : **http://localhost:8001**

### Tester l'API

**Liste des produits :**
```
http://localhost:8001/api/products/
```

**Admin Django :**
```
http://localhost:8001/admin/
```
→ Connectez-vous avec vos identifiants superuser

## 📊 Produits Importés

Après l'import Excel, vous aurez **25 produits** répartis ainsi :

| Catégorie | Nombre | Origine |
|-----------|--------|---------|
| Artisanat | 5 | Afrique |
| Textile | 5 | Afrique |
| Électronique | 5 | Asie |
| Mode | 5 | Afrique |
| Décoration | 5 | Afrique |

## 🔄 Modifier les Produits

### Option 1 : Via Excel (Recommandé)

1. Ouvrir les fichiers dans `backend/data/products_excel/`
2. Modifier les données
3. Sauvegarder
4. Ré-importer :
   ```bash
   python manage.py import_products_excel
   ```

### Option 2 : Via l'Admin Django

1. Aller sur http://localhost:8001/admin/
2. Cliquer sur "Products"
3. Modifier directement

## 📂 Structure des Fichiers Excel

Les fichiers se trouvent dans : `backend/data/products_excel/`

- `artisanat.xlsx` - Masques, statues, sculptures...
- `textile.xlsx` - Tissus wax, pagnes, bogolan...
- `electronique.xlsx` - Smartphones, écouteurs, tablettes...
- `mode.xlsx` - Robes, boubous, ensembles...
- `decoration.xlsx` - Paniers, tableaux, coussins...

## 🛠️ Commandes Utiles

### Voir le nombre de produits
```bash
python manage.py shell -c "from api.models import Product; print(f'Total: {Product.objects.count()} produits')"
```

### Ré-importer depuis zéro
```bash
# Supprimer les produits
python manage.py shell -c "from api.models import Product; Product.objects.all().delete()"

# Ré-importer
python manage.py import_products_excel
```

### Créer de nouveaux fichiers Excel
```bash
python create_excel_samples.py
```

## 🔌 Endpoints API Disponibles

| Endpoint | Description |
|----------|-------------|
| `/api/products/` | Liste tous les produits |
| `/api/products/popular/` | Top 10 produits |
| `/api/products/{id}/` | Détails d'un produit |
| `/api/categories/` | Liste des catégories |
| `/api/suppliers/` | Liste des fournisseurs |
| `/api/orders/` | Gestion des commandes |

## 📖 Documentation Complète

- **Import Excel** : [IMPORT_EXCEL.md](IMPORT_EXCEL.md)
- **API** : [README.md](README.md)

## 🎯 Prochaines Étapes

1. ✅ Backend fonctionne avec produits
2. 🔄 Connecter le frontend Next.js
3. 🎨 Personnaliser les produits Excel selon vos besoins
4. 🚀 Déployer en production

---

**Besoin d'aide ?** Consultez [IMPORT_EXCEL.md](IMPORT_EXCEL.md) pour plus de détails !
