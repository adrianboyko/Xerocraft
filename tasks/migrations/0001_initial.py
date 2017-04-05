# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-05 19:56
from __future__ import unicode_literals

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import tasks.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Claim',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stake_date', models.DateField(auto_now_add=True, help_text='The date on which the member staked this claim.')),
                ('claimed_start_time', models.TimeField(blank=True, help_text='If the task specifies a start time and duration, this must fall within that time span. Otherwise it should be blank.', null=True)),
                ('claimed_duration', models.DurationField(help_text='The amount of work the member plans to do on the task.')),
                ('date_verified', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('C', 'Current'), ('X', 'Expired'), ('Q', 'Queued'), ('A', 'Abandoned'), ('W', 'Working'), ('D', 'Done'), ('U', 'Uninterested')], help_text='The status of this claim.', max_length=1)),
            ],
            bases=(models.Model, tasks.models.TimeWindowedObject),
        ),
        migrations.CreateModel(
            name='Nag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when', models.DateTimeField(auto_now_add=True, help_text='The date and time when member was asked to work the task.')),
                ('auth_token_md5', models.CharField(help_text="MD5 checksum of the random urlsafe base64 string used in the nagging email's URLs.", max_length=32)),
                ('claims', models.ManyToManyField(help_text='The claim that the member was asked to verify.', to='tasks.Claim')),
            ],
        ),
        migrations.CreateModel(
            name='RecurringTaskTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instructions', models.TextField(blank=True, help_text='Instructions for completing the task.', max_length=2048)),
                ('short_desc', models.CharField(help_text='A short description/name for the task.', max_length=40)),
                ('max_workers', models.IntegerField(default=1, help_text='The maximum number of members that can claim/work the task, often 1.')),
                ('max_work', models.DurationField(help_text='The max total amount of hours that can be claimed/worked for this task.')),
                ('work_start_time', models.TimeField(blank=True, help_text="The time at which work on the task must begin. If time doesn't matter, leave blank.", null=True)),
                ('work_duration', models.DurationField(blank=True, help_text='Used with work_start_time to specify the time span over which work must occur. <br/>If work_start_time is blank then this should also be blank.', null=True)),
                ('priority', models.CharField(choices=[('H', 'High'), ('M', 'Medium'), ('L', 'Low')], default='M', help_text='The priority of the task, compared to other tasks.', max_length=1)),
                ('should_nag', models.BooleanField(default=False, help_text='If true, people will be encouraged to work the task via email messages.')),
                ('start_date', models.DateField(help_text='Choose a date for the first instance of the recurring task.')),
                ('active', models.BooleanField(default=True, help_text='Additional tasks will be created only when the template is active.')),
                ('first', models.BooleanField(default=False)),
                ('second', models.BooleanField(default=False)),
                ('third', models.BooleanField(default=False)),
                ('fourth', models.BooleanField(default=False)),
                ('last', models.BooleanField(default=False)),
                ('every', models.BooleanField(default=False)),
                ('monday', models.BooleanField(default=False)),
                ('tuesday', models.BooleanField(default=False)),
                ('wednesday', models.BooleanField(default=False)),
                ('thursday', models.BooleanField(default=False)),
                ('friday', models.BooleanField(default=False)),
                ('saturday', models.BooleanField(default=False)),
                ('sunday', models.BooleanField(default=False)),
                ('jan', models.BooleanField(default=True)),
                ('feb', models.BooleanField(default=True)),
                ('mar', models.BooleanField(default=True)),
                ('apr', models.BooleanField(default=True)),
                ('may', models.BooleanField(default=True)),
                ('jun', models.BooleanField(default=True)),
                ('jul', models.BooleanField(default=True)),
                ('aug', models.BooleanField(default=True)),
                ('sep', models.BooleanField(default=True)),
                ('oct', models.BooleanField(default=True)),
                ('nov', models.BooleanField(default=True)),
                ('dec', models.BooleanField(default=True)),
                ('repeat_interval', models.SmallIntegerField(blank=True, help_text='Minimum number of days between recurrences, e.g. 14 for every two weeks.', null=True)),
                ('missed_date_action', models.CharField(blank=True, choices=[('I', "Don't do anything."), ('S', 'Slide task and all later instances forward.')], default='I', help_text='What should be done if the task is not completed by the deadline date.', max_length=1, null=True)),
                ('default_claimant', models.ForeignKey(blank=True, help_text='Some recurring tasks (e.g. classes) have a default a default claimant (e.g. the instructor).', null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Member')),
                ('eligible_claimants', models.ManyToManyField(blank=True, help_text='Anybody chosen is eligible to claim the task.<br/>', related_name='claimable_TaskTemplates', to='members.Member')),
                ('eligible_tags', models.ManyToManyField(blank=True, help_text='Anybody that has one of the chosen tags is eligible to claim the task.<br/>', related_name='claimable_TaskTemplates', to='members.Tag')),
                ('owner', models.ForeignKey(blank=True, help_text='The member that asked for this task to be created or has taken responsibility for its content.<br/>This is almost certainly not the person who will claim the task and do the work.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_TaskTemplates', to='members.Member')),
                ('reviewer', models.ForeignKey(blank=True, help_text='If required, a member who will review the work once its completed.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewableTaskTemplates', to='members.Member')),
            ],
            options={
                'ordering': ['short_desc', '-sunday', '-monday', '-tuesday', '-wednesday', '-thursday', '-friday', '-saturday'],
            },
        ),
        migrations.CreateModel(
            name='Snippet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The name of the snippet.', max_length=40, validators=[django.core.validators.RegexValidator('^[-a-zA-Z0-1]+$', code='invalid_name', message='Name must only contain letters, numbers, and dashes.')])),
                ('description', models.CharField(help_text='Short description of what the snippet is about.', max_length=128)),
                ('text', models.TextField(help_text='The full text content of the snippet.', max_length=2048)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instructions', models.TextField(blank=True, help_text='Instructions for completing the task.', max_length=2048)),
                ('short_desc', models.CharField(help_text='A short description/name for the task.', max_length=40)),
                ('max_workers', models.IntegerField(default=1, help_text='The maximum number of members that can claim/work the task, often 1.')),
                ('max_work', models.DurationField(help_text='The max total amount of hours that can be claimed/worked for this task.')),
                ('work_start_time', models.TimeField(blank=True, help_text="The time at which work on the task must begin. If time doesn't matter, leave blank.", null=True)),
                ('work_duration', models.DurationField(blank=True, help_text='Used with work_start_time to specify the time span over which work must occur. <br/>If work_start_time is blank then this should also be blank.', null=True)),
                ('priority', models.CharField(choices=[('H', 'High'), ('M', 'Medium'), ('L', 'Low')], default='M', help_text='The priority of the task, compared to other tasks.', max_length=1)),
                ('should_nag', models.BooleanField(default=False, help_text='If true, people will be encouraged to work the task via email messages.')),
                ('creation_date', models.DateField(default=datetime.date.today, help_text='The date on which this task was created in the database.')),
                ('scheduled_date', models.DateField(blank=True, help_text='If appropriate, set a date on which the task must be performed.', null=True)),
                ('orig_sched_date', models.DateField(blank=True, help_text='This is the first value that scheduled_date was set to. Required to avoid recreating a rescheduled task.', null=True)),
                ('deadline', models.DateField(blank=True, help_text='If appropriate, specify a deadline by which the task must be completed.', null=True)),
                ('status', models.CharField(choices=[('A', 'Active'), ('R', 'Reviewable'), ('D', 'Done'), ('C', 'Canceled')], default='A', help_text='The status of this task.', max_length=1)),
                ('claimants', models.ManyToManyField(help_text='The people who say they are going to work on this task.', related_name='tasks_claimed', through='tasks.Claim', to='members.Member')),
                ('depends_on', models.ManyToManyField(help_text='If appropriate, specify what tasks must be completed before this one can start.', related_name='prerequisite_for', to='tasks.Task')),
                ('eligible_claimants', models.ManyToManyField(blank=True, help_text='Anybody chosen is eligible to claim the task.<br/>', related_name='claimable_Tasks', to='members.Member')),
                ('eligible_tags', models.ManyToManyField(blank=True, help_text='Anybody that has one of the chosen tags is eligible to claim the task.<br/>', related_name='claimable_Tasks', to='members.Tag')),
                ('owner', models.ForeignKey(blank=True, help_text='The member that asked for this task to be created or has taken responsibility for its content.<br/>This is almost certainly not the person who will claim the task and do the work.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_Tasks', to='members.Member')),
                ('recurring_task_template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='instances', to='tasks.RecurringTaskTemplate')),
                ('reviewer', models.ForeignKey(blank=True, help_text='If required, a member who will review the work once its completed.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewableTasks', to='members.Member')),
            ],
            options={
                'ordering': ['scheduled_date', 'work_start_time'],
            },
            bases=(models.Model, tasks.models.TimeWindowedObject),
        ),
        migrations.CreateModel(
            name='TaskNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when_written', models.DateTimeField(auto_now_add=True, help_text='The date and time when the note was written.')),
                ('content', models.TextField(help_text='Anything you want to say about the task. Questions, hints, problems, review feedback, etc.', max_length=2048)),
                ('status', models.CharField(choices=[('C', 'Critical'), ('R', 'Resolved'), ('I', 'Informational')], max_length=1)),
                ('author', models.ForeignKey(blank=True, help_text='The member who wrote this note.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='task_notes_authored', to='members.Member')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='tasks.Task')),
            ],
        ),
        migrations.CreateModel(
            name='UnavailableDates',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(help_text='The first date (inclusive) on which the person will be unavailable.')),
                ('end_date', models.DateField(help_text='The last date (inclusive) on which the person will be unavailable.')),
            ],
        ),
        migrations.CreateModel(
            name='Work',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('work_date', models.DateField(help_text='The date on which the work was done.')),
                ('work_duration', models.DurationField(help_text='The amount of time the member spent working.')),
                ('claim', models.ForeignKey(help_text='The claim against which the work is being reported.', on_delete=django.db.models.deletion.PROTECT, to='tasks.Claim')),
            ],
            options={
                'verbose_name_plural': 'Work',
            },
        ),
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('calendar_token', models.CharField(blank=True, help_text='Random hex string used to access calendar.', max_length=32, null=True)),
                ('last_work_mtd_reported', models.DurationField(default=datetime.timedelta(0), help_text='The most recent work MTD total reported to the worker.')),
                ('should_include_alarms', models.BooleanField(default=False, help_text="Controls whether or not a worker's calendar includes alarms.")),
                ('should_nag', models.BooleanField(default=False, help_text='Controls whether ANY nags should be sent to the worker.')),
                ('should_report_work_mtd', models.BooleanField(default=False, help_text='Controls whether reports should be sent to worker when work MTD changes.')),
                ('member', models.OneToOneField(help_text='This must point to the corresponding member.', on_delete=django.db.models.deletion.CASCADE, related_name='worker', to='members.Member')),
            ],
            options={
                'ordering': ['member__auth_user__first_name', 'member__auth_user__last_name'],
            },
        ),
        migrations.CreateModel(
            name='WorkNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when_written', models.DateTimeField(auto_now_add=True, help_text='The date and time when the note was written.')),
                ('content', models.TextField(help_text='Anything you want to say about the work done.', max_length=2048)),
                ('author', models.ForeignKey(blank=True, help_text='The member who wrote this note.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='work_notes_authored', to='members.Member')),
                ('work', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='tasks.Work')),
            ],
        ),
        migrations.AddField(
            model_name='unavailabledates',
            name='who',
            field=models.ForeignKey(blank=True, help_text='The worker who will be unavailable.', null=True, on_delete=django.db.models.deletion.CASCADE, to='tasks.Worker'),
        ),
        migrations.AddField(
            model_name='nag',
            name='tasks',
            field=models.ManyToManyField(help_text='The task that the member was asked to work.', to='tasks.Task'),
        ),
        migrations.AddField(
            model_name='nag',
            name='who',
            field=models.ForeignKey(help_text='The member who was nagged.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Member'),
        ),
        migrations.AddField(
            model_name='claim',
            name='claimed_task',
            field=models.ForeignKey(help_text='The task against which the claim to work is made.', on_delete=django.db.models.deletion.CASCADE, to='tasks.Task'),
        ),
        migrations.AddField(
            model_name='claim',
            name='claiming_member',
            field=models.ForeignKey(help_text='The member claiming the task.', on_delete=django.db.models.deletion.CASCADE, to='members.Member'),
        ),
        migrations.AlterUniqueTogether(
            name='task',
            unique_together=set([('scheduled_date', 'short_desc', 'work_start_time')]),
        ),
        migrations.AlterUniqueTogether(
            name='claim',
            unique_together=set([('claiming_member', 'claimed_task')]),
        ),
    ]
