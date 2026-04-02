from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0004_productomaquillaje_inventario__nombre_398267_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productomaquillaje',
            name='proveedor',
            field=models.CharField(blank=True, default='Sin proveedor', max_length=120),
        ),
    ]
