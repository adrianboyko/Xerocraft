# Generated by Django 2.0.3 on 2018-07-11 06:33

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kmkr', '0010_auto_20180709_1144'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='showtime',
            name='minute_duration',
        ),
        migrations.AddField(
            model_name='show',
            name='duration',
            field=models.DurationField(default=datetime.timedelta(0, 3600), help_text='The duration of the show.'),
        ),
    ]
