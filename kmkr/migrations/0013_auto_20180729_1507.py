# Generated by Django 2.0.3 on 2018-07-29 22:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kmkr', '0012_auto_20180714_2041'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManualPlayList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('show_date', models.DateField(blank=True, help_text='If show is specified, this date specifies a specific instance of it.', null=True)),
                ('sequence', models.IntegerField(help_text='The position of the track in the playlist.')),
                ('artist', models.CharField(blank=True, help_text='The artist who performed the track.', max_length=128)),
                ('title', models.CharField(blank=True, help_text='The title of the track.', max_length=128)),
                ('duration', models.DurationField(blank=True, help_text='The duration of the track.')),
                ('show', models.ForeignKey(blank=True, help_text='The associated show, if track was played as part of a show.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='kmkr.Show')),
            ],
        ),
        migrations.AddField(
            model_name='showtime',
            name='production_method',
            field=models.CharField(choices=[('LIV', 'Live'), ('PRE', 'Prerecorded'), ('RPT', 'Repeat')], default='LIV', help_text='Production method.', max_length=3),
            preserve_default=False,
        ),
    ]
