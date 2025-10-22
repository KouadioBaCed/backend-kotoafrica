"""
Script pour créer des fichiers Excel exemples avec des produits par catégorie
Exécuter: python create_excel_samples.py
"""

import pandas as pd
import os

# Créer le dossier s'il n'existe pas
os.makedirs('data/products_excel', exist_ok=True)

# Produits Artisanat (Afrique)
artisanat_data = {
    'nom': [
        'Masque Baoulé Traditionnel',
        'Statue en Bois d\'Ébène',
        'Sculpture Djembé Décoratif',
        'Masque Dan Authentique',
        'Figurine Akan en Bronze'
    ],
    'description': [
        'Masque africain artisanal sculpté à la main par des artisans ivoiriens. Pièce unique.',
        'Sculpture artisanale en bois d\'ébène représentant une figure traditionnelle. Hauteur 30cm.',
        'Djembé décoratif sculpté à la main avec motifs traditionnels africains.',
        'Masque Dan authentique de Côte d\'Ivoire, utilisé dans les cérémonies.',
        'Figurine artisanale en bronze coulé selon la technique ancestrale Akan.'
    ],
    'prix': [45000, 55000, 38000, 62000, 48000],
    'origine': ['africa', 'africa', 'africa', 'africa', 'africa'],
    'pays': ['Côte d\'Ivoire', 'Côte d\'Ivoire', 'Mali', 'Côte d\'Ivoire', 'Ghana'],
    'stock': [15, 10, 8, 12, 20],
    'delai_livraison': [7, 8, 10, 7, 9],
    'fournisseur': ['Artisanat Ivoirien', 'Artisanat Ivoirien', 'Artisanat Ivoirien', 'Artisanat Ivoirien', 'Ghana Textiles'],
    'categorie': ['Artisanat', 'Artisanat', 'Artisanat', 'Artisanat', 'Artisanat']
}

# Produits Textile (Afrique)
textile_data = {
    'nom': [
        'Tissu Wax Premium',
        'Pagne Kente Authentique',
        'Bogolan du Mali',
        'Tissu Bazin Riche',
        'Wax Hollandais 6 yards'
    ],
    'description': [
        'Tissu africain en coton imprimé wax. Motifs traditionnels colorés. 6 yards.',
        'Pagne Kente tissé traditionnellement. Couleurs vives, motifs symboliques ghanéens.',
        'Tissu bogolan artisanal du Mali teint à la boue avec motifs géométriques.',
        'Bazin riche brodé de qualité supérieure pour grandes occasions.',
        'Tissu wax hollandais authentique, motifs variés, 6 yards par pièce.'
    ],
    'prix': [12000, 28000, 22000, 35000, 18000],
    'origine': ['africa', 'africa', 'africa', 'africa', 'africa'],
    'pays': ['Ghana', 'Ghana', 'Mali', 'Sénégal', 'Ghana'],
    'stock': [50, 30, 25, 20, 45],
    'delai_livraison': [5, 6, 8, 7, 5],
    'fournisseur': ['Ghana Textiles', 'Ghana Textiles', 'Ghana Textiles', 'Senegal Fashion', 'Ghana Textiles'],
    'categorie': ['Textile', 'Textile', 'Textile', 'Textile', 'Textile']
}

# Produits Électronique (Asie)
electronique_data = {
    'nom': [
        'Smartphone Android 12',
        'Écouteurs Bluetooth TWS',
        'Montre Connectée Smart',
        'Tablette Android 10 pouces',
        'Power Bank 20000mAh'
    ],
    'description': [
        'Smartphone dernière génération avec écran AMOLED 6.5", 128GB stockage, appareil photo 48MP.',
        'Écouteurs sans fil avec réduction de bruit active, autonomie 24h avec boîtier de charge.',
        'Montre intelligente avec suivi santé, notifications, étanche IP68. Autonomie 7 jours.',
        'Tablette tactile 10", 64GB, processeur Octa-core, idéale pour multimédia et productivité.',
        'Batterie externe 20000mAh avec charge rapide, 2 ports USB, LED. Compatible tous appareils.'
    ],
    'prix': [85000, 15000, 25000, 65000, 12000],
    'origine': ['asia', 'asia', 'asia', 'asia', 'asia'],
    'pays': ['Chine', 'Chine', 'Chine', 'Chine', 'Chine'],
    'stock': [200, 150, 80, 45, 120],
    'delai_livraison': [14, 12, 10, 12, 10],
    'fournisseur': ['Asian Electronics Co.', 'Asian Electronics Co.', 'Asian Electronics Co.', 'Asian Electronics Co.', 'Asian Electronics Co.'],
    'categorie': ['Électronique', 'Électronique', 'Électronique', 'Électronique', 'Électronique']
}

# Produits Mode (Afrique)
mode_data = {
    'nom': [
        'Robe Africaine Bazin',
        'Boubou Brodé Homme',
        'Ensemble Pagne Complet',
        'Chemise Wax Homme',
        'Robe Dashiki Femme'
    ],
    'description': [
        'Robe élégante en bazin riche brodé. Confection artisanale, disponible en plusieurs tailles.',
        'Boubou traditionnel brodé à la main. Tissu en coton premium, motifs élégants.',
        'Ensemble complet: jupe, haut et foulard en pagne wax coordonné.',
        'Chemise homme en tissu wax, coupe moderne, motifs africains contemporains.',
        'Robe dashiki colorée, coupe fluide, idéale pour toutes occasions.'
    ],
    'prix': [35000, 42000, 28000, 18000, 22000],
    'origine': ['africa', 'africa', 'africa', 'africa', 'africa'],
    'pays': ['Sénégal', 'Sénégal', 'Ghana', 'Côte d\'Ivoire', 'Ghana'],
    'stock': [25, 18, 30, 40, 35],
    'delai_livraison': [6, 7, 5, 6, 5],
    'fournisseur': ['Senegal Fashion', 'Senegal Fashion', 'Ghana Textiles', 'Artisanat Ivoirien', 'Ghana Textiles'],
    'categorie': ['Mode', 'Mode', 'Mode', 'Mode', 'Mode']
}

# Produits Décoration (Afrique)
decoration_data = {
    'nom': [
        'Panier Artisanal Bolga',
        'Tableau Batik Africain',
        'Coussin Bogolan',
        'Lampe Calebasse Sculptée',
        'Tenture Murale Kente'
    ],
    'description': [
        'Panier tissé à la main en fibres naturelles. Design coloré traditionnel du Ghana.',
        'Tableau décoratif en batik fait main. Scènes de vie africaine, dimensions 60x80cm.',
        'Coussin décoratif en tissu bogolan du Mali avec housse amovible 45x45cm.',
        'Lampe artisanale en calebasse sculptée avec motifs traditionnels et LED.',
        'Tenture murale en tissu Kente authentique, motifs symboliques, 100x150cm.'
    ],
    'prix': [8000, 38000, 15000, 32000, 45000],
    'origine': ['africa', 'africa', 'africa', 'africa', 'africa'],
    'pays': ['Ghana', 'Côte d\'Ivoire', 'Mali', 'Sénégal', 'Ghana'],
    'stock': [40, 12, 28, 15, 10],
    'delai_livraison': [5, 9, 7, 8, 6],
    'fournisseur': ['Ghana Textiles', 'Artisanat Ivoirien', 'Ghana Textiles', 'Senegal Fashion', 'Ghana Textiles'],
    'categorie': ['Décoration', 'Décoration', 'Décoration', 'Décoration', 'Décoration']
}

# Créer les DataFrames et sauvegarder en Excel
categories = {
    'artisanat': artisanat_data,
    'textile': textile_data,
    'electronique': electronique_data,
    'mode': mode_data,
    'decoration': decoration_data
}

for category_name, data in categories.items():
    df = pd.DataFrame(data)
    filename = f'data/products_excel/{category_name}.xlsx'
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f'✅ Créé: {filename} ({len(df)} produits)')

print('\n🎉 Tous les fichiers Excel ont été créés avec succès!')
print('\nFichiers créés dans: backend/data/products_excel/')
print('- artisanat.xlsx')
print('- textile.xlsx')
print('- electronique.xlsx')
print('- mode.xlsx')
print('- decoration.xlsx')
