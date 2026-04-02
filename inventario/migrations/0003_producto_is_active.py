from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0002_auto_20260330_2042'),
    ]

    operations = [
        migrations.AddField(
            model_name='productomaquillaje',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
