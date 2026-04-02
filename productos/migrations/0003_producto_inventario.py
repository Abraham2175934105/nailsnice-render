from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
        ('productos', '0002_alter_categoria_options_alter_producto_descripcion'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='inventario',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='producto_catalogo', to='inventario.productomaquillaje', unique=True),
        ),
    ]
