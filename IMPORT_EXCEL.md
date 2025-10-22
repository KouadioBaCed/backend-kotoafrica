# Import de Produits depuis Excel

Ce guide explique comment importer des produits dans KÔTO AFRICA depuis des fichiers Excel par catégorie.

## 📋 Format des Fichiers Excel

Chaque fichier Excel doit contenir les colonnes suivantes :

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `nom` | Texte | Nom du produit | Masque Baoulé Traditionnel |
| `description` | Texte | Description détaillée | Masque africain artisanal sculpté... |
| `prix` | Nombre | Prix en FCFA | 45000 |
| `origine` | Texte | `africa` ou `asia` | africa |
| `pays` | Texte | Pays d'origine | Côte d'Ivoire |
| `stock` | Nombre | Quantité en stock | 15 |
| `delai_livraison` | Nombre | Délai en jours | 7 |
| `fournisseur` | Texte | Nom du fournisseur | Artisanat Ivoirien |
| `categorie` | Texte | Catégorie du produit | Artisanat |

## 🗂️ Catégories Disponibles

- **Artisanat** - Produits artisanaux africains
- **Textile** - Tissus et textiles
- **Électronique** - Appareils électroniques
- **Mode** - Vêtements et accessoires
- **Décoration** - Articles de décoration

## 👥 Fournisseurs Disponibles

### Fournisseurs Africains
- **Artisanat Ivoirien** (Côte d'Ivoire)
- **Ghana Textiles** (Ghana)
- **Senegal Fashion** (Sénégal)

### Fournisseurs Asiatiques
- **Asian Electronics Co.** (Chine)

## 🚀 Instructions d'Utilisation

### Étape 1 : Installer les dépendances

```bash
pip install openpyxl pandas
```

Ou simplement :
```bash
pip install -r requirements.txt
```

### Étape 2 : Créer les fichiers Excel exemples

```bash
cd backend
python create_excel_samples.py
```

Cela créera automatiquement 5 fichiers Excel dans `backend/data/products_excel/` :
- `artisanat.xlsx` (5 produits)
- `textile.xlsx` (5 produits)
- `electronique.xlsx` (5 produits)
- `mode.xlsx` (5 produits)
- `decoration.xlsx` (5 produits)

### Étape 3 : Importer les produits

```bash
python manage.py import_products_excel
```

Cette commande va :
1. ✅ Créer les catégories si elles n'existent pas
2. ✅ Créer les fournisseurs si ils n'existent pas
3. ✅ Lire tous les fichiers `.xlsx` dans `data/products_excel/`
4. ✅ Importer ou mettre à jour les produits

## 📝 Personnaliser les Fichiers Excel

### Option 1 : Modifier les fichiers générés

1. Ouvrez les fichiers Excel dans `backend/data/products_excel/`
2. Modifiez les données selon vos besoins
3. Ajoutez de nouvelles lignes pour plus de produits
4. Sauvegardez les fichiers
5. Re-exécutez `python manage.py import_products_excel`

### Option 2 : Créer vos propres fichiers

1. Créez un nouveau fichier `.xlsx` dans `backend/data/products_excel/`
2. Respectez le format des colonnes (voir tableau ci-dessus)
3. Nommez le fichier selon la catégorie (ex: `bijoux.xlsx`)
4. Exécutez `python manage.py import_products_excel`

## 📊 Exemple de Fichier Excel

Voici à quoi ressemble un fichier Excel type :

| nom | description | prix | origine | pays | stock | delai_livraison | fournisseur | categorie |
|-----|-------------|------|---------|------|-------|-----------------|-------------|-----------|
| Masque Baoulé | Masque artisanal... | 45000 | africa | Côte d'Ivoire | 15 | 7 | Artisanat Ivoirien | Artisanat |
| Tissu Wax | Tissu africain... | 12000 | africa | Ghana | 50 | 5 | Ghana Textiles | Textile |

## ⚙️ Commandes Utiles

### Voir les produits importés
```bash
python manage.py shell
>>> from api.models import Product
>>> Product.objects.all()
>>> Product.objects.count()
```

### Supprimer tous les produits
```bash
python manage.py shell
>>> from api.models import Product
>>> Product.objects.all().delete()
```

### Ré-importer depuis zéro
```bash
# Supprimer les produits existants
python manage.py shell -c "from api.models import Product; Product.objects.all().delete()"

# Ré-importer
python manage.py import_products_excel
```

## 🔧 Dépannage

### Erreur : "Aucun fichier Excel trouvé"
- Vérifiez que le dossier `backend/data/products_excel/` existe
- Exécutez `python create_excel_samples.py` pour créer les fichiers exemples

### Erreur : "Colonnes manquantes"
- Vérifiez que votre fichier Excel contient toutes les colonnes requises
- Respectez l'orthographe exacte des noms de colonnes

### Erreur : "Fournisseur non trouvé"
- Utilisez un des fournisseurs existants listés ci-dessus
- Ou créez d'abord le fournisseur dans l'admin Django

### Erreur : "Catégorie non trouvée"
- Utilisez une des catégories listées ci-dessus
- Respectez l'orthographe (avec ou sans accents)

## 📍 Structure des Fichiers

```
backend/
├── data/
│   └── products_excel/          # Dossier des fichiers Excel
│       ├── artisanat.xlsx
│       ├── textile.xlsx
│       ├── electronique.xlsx
│       ├── mode.xlsx
│       └── decoration.xlsx
├── create_excel_samples.py      # Script pour créer les exemples
└── manage.py
```

## 🎯 Workflow Recommandé

1. **Développement** : Utiliser les fichiers Excel exemples
   ```bash
   python create_excel_samples.py
   python manage.py import_products_excel
   ```

2. **Production** : Créer vos propres fichiers Excel avec vos produits réels
   ```bash
   # Créer vos fichiers dans data/products_excel/
   python manage.py import_products_excel
   ```

3. **Mise à jour** : Modifier les Excel et ré-importer
   ```bash
   python manage.py import_products_excel  # Met à jour automatiquement
   ```

## 📈 Avantages de cette Approche

✅ **Simple** : Gérer les produits dans Excel (familier)
✅ **Flexible** : Ajouter/modifier facilement en masse
✅ **Organisé** : Un fichier par catégorie
✅ **Traçable** : Les fichiers Excel servent de source de vérité
✅ **Collaboratif** : Plusieurs personnes peuvent préparer les fichiers

---

**Note** : Les fichiers Excel exemples contiennent 25 produits au total pour démarrer rapidement !
