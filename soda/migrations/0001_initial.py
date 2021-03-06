# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-07 21:51
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="The name of the product, for example 'Diet Coke'", max_length=40, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='SkuToProductMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku_or_desc', models.CharField(help_text='The SKU (or description) the payment processor will report.', max_length=40, unique=True)),
                ('product', models.ForeignKey(help_text='The product that the SKU (or description) identifies.', on_delete=django.db.models.deletion.CASCADE, to='soda.Product')),
            ],
        ),
        migrations.CreateModel(
            name='VendingMachineBin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(help_text='The bin number, 1 or greater.', unique=True)),
                ('contents', models.ForeignKey(help_text='The product currently stocked in this bin.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='soda.Product')),
            ],
            options={
                'ordering': ['number'],
            },
        ),
        migrations.CreateModel(
            name='VendLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when', models.DateTimeField(auto_now_add=True, help_text='Date and time that the product was vended.')),
                ('product', models.ForeignKey(help_text='The product that was vended.', on_delete=django.db.models.deletion.PROTECT, to='soda.Product')),
                ('who_for', models.ForeignKey(help_text='Who was this product vended for?', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
