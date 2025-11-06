"""
Script pour initialiser les tarifs logistiques par défaut
Execute avec: python manage.py shell < initialize_logistics.py
"""
from api.models import LogisticsRate, ExchangeRate

# Supprimer les données existantes (optionnel)
LogisticsRate.objects.all().delete()
ExchangeRate.objects.all().delete()

# Créer les tarifs logistiques
logistics_rates = [
    {
        'shipping_method': 'air_rapide',
        'rate_per_kg': 17000,
        'rate_per_m3': None,
        'min_days': 10,
        'max_days': 17,
        'is_active': True
    },
    {
        'shipping_method': 'air_express',
        'rate_per_kg': 27000,
        'rate_per_m3': None,
        'min_days': 3,
        'max_days': 8,
        'is_active': True
    },
    {
        'shipping_method': 'sea_no_motor',
        'rate_per_kg': None,
        'rate_per_m3': 220000,
        'min_days': 40,
        'max_days': 70,
        'is_active': True
    },
    {
        'shipping_method': 'sea_with_motor',
        'rate_per_kg': None,
        'rate_per_m3': 260000,
        'min_days': 40,
        'max_days': 70,
        'is_active': True
    },
]

for rate_data in logistics_rates:
    LogisticsRate.objects.create(**rate_data)
    print(f"✓ Created {rate_data['shipping_method']}")

# Créer le taux de change par défaut
exchange_rate = ExchangeRate.objects.create(
    usd_to_fcfa=661.28,
    is_active=True
)
print(f"✓ Created exchange rate: 1 USD = {exchange_rate.usd_to_fcfa} FCFA")

print("\n🎉 Logistics rates initialized successfully!")
