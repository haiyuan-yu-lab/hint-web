# Generated by Django 5.0.2 on 2024-03-14 21:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_rename_oldversionmetadata_downloadfilemetadata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downloadfilemetadata',
            name='interaction_count',
            field=models.IntegerField(default=0),
        ),
    ]
