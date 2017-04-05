# Standard
import logging
from datetime import date, timedelta

# Third Party
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

# Local
from members.models import Member, Tagging, VisitEvent, Pushover
from tasks.models import Task, Worker, Claim, Nag, RecurringTaskTemplate
import members.notifications as notifications

__author__ = 'Adrian'

logger = logging.getLogger("tasks")


@receiver(post_save, sender=Tagging)
def act_on_new_tag(sender, **kwargs):
    if kwargs.get('created', True):
        pass
        """ TODO: Check to see if this new tagging makes the tagged_member eligible for a task
            they weren't previously eligible for. If so, email them with info.
        """


@receiver(post_save, sender=Member)
def create_default_worker(sender, **kwargs):
    if kwargs.get('created', True):
        w,_ = Worker.objects.get_or_create(member=kwargs.get('instance'))


@receiver(pre_save, sender=Claim)
def staffing_update_notification(sender, **kwargs):
    try:
        if kwargs.get('created', True):
            claim = kwargs.get('instance')  # type: Claim
            message = None
            if claim.status in [Claim.STAT_UNINTERESTED, Claim.STAT_ABANDONED, Claim.STAT_EXPIRED]:
                message = "{0} will NOT work '{1}' on {2:%a %m/%d}".format(
                    claim.claiming_member.friendly_name,
                    claim.claimed_task.short_desc,
                    claim.claimed_task.scheduled_date
                )
            if claim.status == Claim.STAT_CURRENT and claim.date_verified is not None:
                message = "{0} WILL work '{1}' on {2:%a %m/%d}".format(
                    claim.claiming_member.friendly_name,
                    claim.claimed_task.short_desc,
                    claim.claimed_task.scheduled_date
                )
            if message is not None:
                recipient = Member.objects.get(auth_user__username='adrianb')
                notifications.notify(recipient, "Staffing Update", message)

    except Exception as e:
        logger.error("Problem sending staffing update.")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# VISIT
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# HOST = "http://192.168.1.101:8000"  # For testing
HOST = "https://" + Site.objects.get_current().domain


@receiver(post_save, sender=VisitEvent)
def maintenance_nag(sender, **kwargs):
    try:
        visit = kwargs.get('instance')  # type: VisitEvent

        # We're only interested in arrivals
        if visit.event_type != VisitEvent.EVT_ARRIVAL:
            return

        # Only act on a member's first visit of the day.
        num_visits_today = VisitEvent.objects.filter(
            who=visit.who,
            event_type=VisitEvent.EVT_ARRIVAL,
            when__gte=date.today(),
        ).count()
        if num_visits_today > 1:
            return

        # This gets tasks that are scheduled like maintenance tasks.
        # I.e. those that need to be done every X days, but can slide.
        tasks = Task.objects.filter(
            eligible_claimants=visit.who,
            scheduled_date=date.today(),
            status=Task.STAT_ACTIVE,
            should_nag=True,
            recurring_task_template__repeat_interval__isnull=False,
            recurring_task_template__missed_date_action=RecurringTaskTemplate.MDA_SLIDE_SELF_AND_LATER,
        )

        # Nag by sending a notification for each task the member could work.
        for task in tasks:  # type: Task

            # Create the nag
            b64, md5 = Member.generate_auth_token_str(
                lambda token: Nag.objects.filter(auth_token_md5=token).count() == 0  # uniqueness test
            )
            nag = Nag.objects.create(who=visit.who, auth_token_md5=md5)
            nag.tasks.add(task)

            # Generate an informative message
            try:
                last_done = Task.objects.filter(
                    scheduled_date__lt=date.today(),
                    status=Task.STAT_DONE,
                    recurring_task_template=task.recurring_task_template,
                ).latest('scheduled_date')
                delta = date.today() - last_done.scheduled_date  # type: timedelta
                message = "This task was last completed {} days ago!".format(delta.days)
            except Task.DoesNotExist:
                message = ""
            message += " If you can complete this task today, please click the link AFTER the work is done."

            relative = reverse('task:note-task-done', kwargs={'task_pk': task.id, 'auth_token': b64})
            # Send the notification
            notifications.notify(
                visit.who,
                task.short_desc,
                message,
                url=HOST+relative,
                url_title="I Did It!",
            )

            # Send a notification to manager(s) to let them know that somebody was asked to do the task.
            # TODO: Shouldn't have a hard-coded userid here. Make configurable, perhaps with tags.
            mgr = Member.objects.get(auth_user__username='adrianb')
            if visit.who != mgr:
                notifications.notify(
                    mgr,
                    task.short_desc,
                    visit.who.friendly_name + " was asked to work this task.",
                )

    except Exception as e:
        # Makes sure that problems here do not prevent subsequent processing.
        logger.error("Problem in maintenance_nag: %s", str(e))

