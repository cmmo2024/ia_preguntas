# Generated by Django 5.2.3 on 2025-06-30 00:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Descripción'),
        ),
    ]
