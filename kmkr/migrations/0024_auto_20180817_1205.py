# Generated by Django 2.0.3 on 2018-08-17 19:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kmkr', '0023_auto_20180814_2027'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='broadcast',
            options={'verbose_name': 'Episode broadcast'},
        ),
        migrations.AlterModelOptions(
            name='episodetrack',
            options={'verbose_name': 'Track for episode', 'verbose_name_plural': 'Tracks for episode'},
        ),
        migrations.AlterModelOptions(
            name='onairpersonality',
            options={'verbose_name': 'On air personality', 'verbose_name_plural': 'On air personalities'},
        ),
        migrations.AlterModelOptions(
            name='onairpersonalitysocialmedia',
            options={'verbose_name': "On Air Personality's Social Acct"},
        ),
        migrations.AlterModelOptions(
            name='playlogentry',
            options={'verbose_name': 'Track broadcast', 'verbose_name_plural': 'Tracks broadcast'},
        ),
        migrations.AlterModelOptions(
            name='track',
            options={'verbose_name': 'Track in library', 'verbose_name_plural': 'Tracks in library'},
        ),
        migrations.AlterModelOptions(
            name='underwritinglogentry',
            options={'verbose_name': 'Underwriting broadcast'},
        ),
        migrations.AlterModelOptions(
            name='underwritingspots',
            options={'verbose_name': 'Underwriting spot'},
        ),
        migrations.AddField(
            model_name='playlogentry',
            name='non_library_track',
            field=models.ForeignKey(blank=True, help_text='The NON-library track which was played.', null=True, on_delete=django.db.models.deletion.PROTECT, to='kmkr.EpisodeTrack'),
        ),
        migrations.AlterField(
            model_name='playlogentry',
            name='track',
            field=models.ForeignKey(blank=True, help_text='The library track which was played.', null=True, on_delete=django.db.models.deletion.PROTECT, to='kmkr.Track'),
        ),
    ]
