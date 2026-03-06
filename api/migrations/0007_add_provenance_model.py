# Custom migration: Create Provenance model and migrate Product.origin

import django.db.models.deletion
from django.db import migrations, models


def populate_provenances_and_map_products(apps, schema_editor):
    """Create default provenances and map existing products."""
    Provenance = apps.get_model('api', 'Provenance')
    Product = apps.get_model('api', 'Product')

    # Create default provenances
    afrique, _ = Provenance.objects.get_or_create(
        slug='africa',
        defaults={'name': 'Afrique', 'description': "Produits en provenance d'Afrique"}
    )
    asie, _ = Provenance.objects.get_or_create(
        slug='asia',
        defaults={'name': 'Asie', 'description': "Produits en provenance d'Asie"}
    )

    # Map existing products based on old origin CharField value
    for product in Product.objects.all():
        if product.origin_old == 'africa':
            product.origin_new = afrique
        elif product.origin_old == 'asia':
            product.origin_new = asie
        product.save()


def reverse_migration(apps, schema_editor):
    """Reverse: map FK back to string values."""
    Product = apps.get_model('api', 'Product')
    for product in Product.objects.select_related('origin_new').all():
        if product.origin_new:
            product.origin_old = product.origin_new.slug
            product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_quoterequest_order_quoterequest_payment_status_and_more'),
    ]

    operations = [
        # Step 1: Create Provenance model
        migrations.CreateModel(
            name='Provenance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Provenance',
                'verbose_name_plural': 'Provenances',
                'db_table': 'provenances',
                'ordering': ['name'],
            },
        ),

        # Step 2: Rename old origin field to origin_old
        migrations.RenameField(
            model_name='product',
            old_name='origin',
            new_name='origin_old',
        ),

        # Step 3: Add new FK field origin_new
        migrations.AddField(
            model_name='product',
            name='origin_new',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products_new',
                to='api.provenance',
            ),
        ),

        # Step 4: Populate provenances and map products
        migrations.RunPython(populate_provenances_and_map_products, reverse_migration),

        # Step 5: Remove old origin CharField
        migrations.RemoveField(
            model_name='product',
            name='origin_old',
        ),

        # Step 6: Rename origin_new to origin
        migrations.RenameField(
            model_name='product',
            old_name='origin_new',
            new_name='origin',
        ),

        # Step 7: Update the field to match model definition (related_name)
        migrations.AlterField(
            model_name='product',
            name='origin',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='api.provenance',
            ),
        ),
    ]
