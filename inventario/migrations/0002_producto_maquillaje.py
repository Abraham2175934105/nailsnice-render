from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductoMaquillaje',
            fields=[
                ('id_inventario', models.BigAutoField(primary_key=True, db_column='id_inventario', serialize=False)),
                ('nombre', models.CharField(max_length=160)),
                ('cantidad', models.PositiveIntegerField(default=0)),
                ('estado', models.CharField(default='disponible', max_length=40)),
                ('fecha_ingreso', models.DateField(blank=True, null=True)),
                ('stock', models.IntegerField(default=0)),
                ('precio', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('marca', models.CharField(blank=True, max_length=120, null=True)),
                ('proveedor', models.CharField(blank=True, max_length=120, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('imagen', models.CharField(blank=True, max_length=255, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'producto_inventario',
                'managed': True,
            },
        ),
    ]
