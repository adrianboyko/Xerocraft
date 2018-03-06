# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-03-06 19:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0011_auto_20171216_0951'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershipgiftcard',
            name='campaign',
            field=models.ForeignKey(blank=True, help_text='The membership campaign that this card/code belongs to, if any.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.MembershipCampaign'),
        ),
    ]
