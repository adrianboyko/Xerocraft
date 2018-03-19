# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-03-18 20:53
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('members', '0016_auto_20180318_1353'),
    ]

    operations = [
        migrations.RunSQL(
            "INSERT INTO members_externalid SELECT * FROM social_auth_usersocialauth"
        )
    ]
