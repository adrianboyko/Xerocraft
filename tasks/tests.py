# Standard
from datetime import datetime, date, timedelta, time
from pydoc import locate  # for loading classes
import os

# Third Party
from django.core import management, mail
from django.urls import reverse
from django.test import TestCase, TransactionTestCase, LiveServerTestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.contrib.admin import site
from django.core.management import call_command
from django.utils import timezone
from django.conf import settings
from freezegun import freeze_time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import lxml.html
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

# Local
from tasks.models import (
    RecurringTaskTemplate, TemplateEligibleClaimant2,
    Task, TaskNote, EligibleClaimant2,
    Claim,
    Work, WorkNote,
    Nag,
    Snippet,
    Worker

)
from members.models import Member, VisitEvent
import tasks.restapi as restapi
from members.notifications import notify

USER_VOLUNTEER = settings.BZWOPS_TASKS_CONFIG.get("USER_VOLUNTEER", None)

ONEDAY = timedelta(days=1)
TWODAYS   = 2 * ONEDAY
THREEDAYS = 3 * ONEDAY
FOURDAYS  = 4 * ONEDAY

ONEHOUR = timedelta(hours=1)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class Test_VerifyClaim_Base(LiveServerTestCase):

    SHORT_DESC = "Task With Default Claimant"
    EMAIL1 = 'm1@example.com'
    EMAIL2 = 'm2@example.com'
    EMAIL3 = 'm3@example.com'

    def testScenario(self):

        self.memb1 = User.objects.create_superuser(username='m1', password='123', email=self.EMAIL1).member
        self.memb2 = User.objects.create_superuser(username='m2', password='123', email=self.EMAIL2).member
        self.memb3 = User.objects.create_superuser(username='m3', password='123', email=self.EMAIL3).member

        self.memb1.worker.should_nag = True
        self.memb2.worker.should_nag = True
        self.memb3.worker.should_nag = True

        self.memb1.worker.save()
        self.memb2.worker.save()
        self.memb3.worker.save()

        rt = RecurringTaskTemplate.objects.create(
            short_desc=self.SHORT_DESC,
            max_work=timedelta(hours=1.0),
            start_date=date.today(),
            repeat_interval=1,
            default_claimant=self.memb1,
            should_nag=True,
        )
        rt.save()
        rt.full_clean()

        TemplateEligibleClaimant2.objects.create(template=rt, member=self.memb2)
        TemplateEligibleClaimant2.objects.create(template=rt, member=self.memb3)

        management.call_command("scheduletasks", "0")
        self.task = rt.instances.all()[0]

        # See: https://www.amihaiemil.com/2017/07/14/selenium-headless-chrome-travis.html
        # See: https://stackoverflow.com/questions/50642308/webdriverexception-unknown-error-devtoolsactiveport-file-doesnt-exist-while-t
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location="/usr/bin/google-chrome-stable"
        self.browser = webdriver.Chrome(chrome_options=chrome_options)

        try:
            for offset in range(-4, 2):
                with freeze_time(self.task.scheduled_date + offset*ONEDAY):
                    self.assertEqual(self.task.scheduled_date + offset*ONEDAY, date.today())  # Testing the freeze
                    management.call_command("nag", host=self.live_server_url)
                    if offset < 0: sign_name = "minus"
                    elif offset == 0: sign_name = ""
                    else: sign_name = "plus"
                    method_name = "do_day_{}{}".format(sign_name, str(abs(offset)))
                    if hasattr(self, method_name):
                        getattr(self, method_name)()
        finally:
            self.browser.quit()


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class Test_VerifyClaim_Scenario1(Test_VerifyClaim_Base):

    """ In this scenario, the default claimant ignores the first nag but responds affirmatively to the second."""

    def do_day_minus4(self):
        self.assertEqual(len(mail.outbox), 1)
        (html, ctype) = mail.outbox[0].alternatives[0]
        self.assertEqual(ctype, "text/html")

    def do_day_minus3(self):
        self.assertEqual(len(mail.outbox), 2)
        (html, ctype) = mail.outbox[1].alternatives[0]
        self.assertEqual(ctype, "text/html")
        html_dom = lxml.html.fromstring(html)
        yes_url = html_dom.xpath("//a[@id='Y']/@href")[0]
        self.browser.get(yes_url)

    def do_day_minus2(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)
        self.assertEqual(len(mail.outbox), 2)

    def do_day_minus1(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)
        self.assertEqual(len(mail.outbox), 2)

    def do_day_0(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)
        self.assertEqual(len(mail.outbox), 2)

    def do_day_plus1(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)
        self.assertEqual(len(mail.outbox), 2)


class Test_VerifyClaim_Scenario2(Test_VerifyClaim_Base):

    """In this scenario, nobody responds to any of the generated email messages."""

    def do_day_minus4(self):
        self.assertEqual(len(mail.outbox), 1)
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)

    def do_day_minus3(self):
        self.assertEqual(len(mail.outbox), 2)
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)

    def do_day_minus2(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_EXPIRED)
        self.assertEqual(len(mail.outbox), 5)

    def do_day_minus1(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_EXPIRED)
        self.assertEqual(len(mail.outbox), 8)

    def do_day_0(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_EXPIRED)
        self.assertEqual(len(mail.outbox), 11)

    def do_day_plus1(self):
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_EXPIRED)
        self.assertEqual(len(mail.outbox), 11)


class Test_VerifyClaim_Scenario3(Test_VerifyClaim_Base):

    """
    In this scenario:
        * The default assignee responds negatively on D-4
        * A backup picks up the task on D-2
        * The original default assignee decides to respond affirmatively on D-1, but it's too late.
    """

    def do_day_minus4(self):

        # There is one claim on the task, for the default assignee
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].status, Claim.STAT_CURRENT)

        # Default assignee looks at the email message
        self.assertEqual(len(mail.outbox), 1)
        (html, ctype) = mail.outbox[0].alternatives[0]
        self.assertEqual(ctype, "text/html")
        html_dom = lxml.html.fromstring(html)

        # And responds negatively
        no_url = html_dom.xpath("//a[@id='N']/@href")[0]
        self.browser.get(no_url)

        # http://www.obeythetestinggoat.com/how-to-get-selenium-to-wait-for-page-load-after-a-click.html
        try:
            self.browser.implicitly_wait(60)
            self.browser.find_element_by_partial_link_text("Calendar")
        except NoSuchElementException as e:
            print(self.browser.page_source)
            raise e

        # So, there is now exactly one claim and it's status is UNINTERESTED
        self.assertEqual(len(self.task.claim_set.all()), 1)
        self.assertEqual(len(self.task.claim_set.filter(status=Claim.STAT_ABANDONED)), 1)
        claim = Claim.objects.filter(status=Claim.STAT_ABANDONED).all()[0]  # type: Claim
        self.assertEqual(claim.claiming_member, self.memb1)

    def do_day_minus3(self):
        # Nothing happens on this day in this scenario
        self.assertEqual(len(mail.outbox), 1)

    def do_day_minus2(self):

        # Email went to two backups
        self.assertEqual(len(mail.outbox), 3)

        # One of the backups looks at the task info
        (html, ctype) = mail.outbox[2].alternatives[0]
        self.assertEqual(ctype, "text/html")
        html_dom = lxml.html.fromstring(html)
        task_url = html_dom.xpath("//a/@href")[0]
        self.browser.get(task_url)

        # And decides to take the task
        # http://www.obeythetestinggoat.com/how-to-get-selenium-to-wait-for-page-load-after-a-click.html
        self.browser.implicitly_wait(60)
        self.browser.find_element_by_partial_link_text("Claim").click()
        self.browser.find_element_by_partial_link_text("Calendar")

        # There are now 2 claims for the task: 1 uninterested, 1 current.
        claims = self.task.claim_set.all()
        self.assertEqual(len(claims), 2)
        self.assertTrue(self.task.is_fully_claimed)

    def do_day_minus1(self):

        # No email generated on this day
        self.assertEqual(len(mail.outbox), 3)

        # Default assignee looks at the original email message, again
        (html, ctype) = mail.outbox[0].alternatives[0]
        self.assertEqual(ctype, "text/html")
        html_dom = lxml.html.fromstring(html)

        # And responds affirmatively.
        # But his original claim is gone so he's redirected to offer_task which tells him the task has been claimed.
        yes_url = html_dom.xpath("//a[@id='Y']/@href")[0]
        try:
            self.browser.get(yes_url)
            self.assertTrue("already staffed" in self.browser.page_source)
        except:
            self.fail("Bad (or no) response from: "+yes_url)

    def do_day_0(self):
        # Nothing happens on this day in this scenario
        self.assertEqual(len(mail.outbox), 3)

    def do_day_plus1(self):
        # Nothing happens on this day in this scenario
        self.assertEqual(len(mail.outbox), 3)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class TestTemplateToInstanceCopy(TransactionTestCase):

    def setUp(self):
        self.rt = RecurringTaskTemplate.objects.create(
            short_desc = "a test",
            max_work = timedelta(hours=1.5),
            start_date = date.today(),
            repeat_interval = 1,
        )
        self.rt.full_clean()
        self.rt.save()

    def test_field_copies(self):
        self.rt.create_tasks(max_days_in_advance=2)
        task = Task.objects.all()[:1].get()
        template = task.recurring_task_template

        # REVIEW: Is there a way to dynamically discover and test mixin fields instead of hard-coding them?

        self.assertEqual(task.owner, template.owner)
        self.assertEqual(task.instructions, template.instructions)
        self.assertEqual(task.short_desc, template.short_desc)
        self.assertEqual(task.max_workers, template.max_workers)
        self.assertEqual(task.reviewer, template.reviewer)
        self.assertEqual(task.max_work, template.max_work)
        self.assertEqual(set(task.all_eligible_claimants()), set(template.all_eligible_claimants()))
        self.assertEqual(task.anybody_is_eligible, template.anybody_is_eligible)


class TestRecurringTaskTemplateCertainDays(TestCase):

    def setUp(self):
        self.rt = RecurringTaskTemplate.objects.create(
            short_desc = "a test",
            max_work = timedelta(hours=1.5),
            start_date = date.today(),
            last = True,
            sunday = True,
        )
        self.rt.full_clean()

    def test_greatest_scheduled_date(self):
        sched = self.rt.greatest_scheduled_date()
        start = self.rt.start_date
        self.assertTrue(type(sched) is date and type(start) is date)
        self.assertGreater(self.rt.start_date, sched)

    def test_create_tasks(self):
        self.rt.create_tasks(max_days_in_advance=34)
        count = len(Task.objects.all())
        self.assertTrue(count in [1, 2])
        # create_tasks should be idempotent for a particular argument.
        self.rt.create_tasks(max_days_in_advance=34)
        self.assertEqual(len(Task.objects.all()), count)


class TestRecurringTaskTemplateIntervals(TransactionTestCase):

    def setUp(self):
        self.rt = RecurringTaskTemplate.objects.create(
            short_desc = "a test",
            max_work = timedelta(hours=1.5),
            start_date = date.today(),
            repeat_interval = 28)
        self.rt.full_clean()

    def test_create_tasks(self):
        self.rt.create_tasks(365)
        self.assertEqual(len(Task.objects.all()), 13)
        # create_tasks should be idempotent for a particular argument.
        self.rt.create_tasks(365)
        self.assertEqual(len(Task.objects.all()), 13)


class TestPriorityMatch(TestCase):

    def testPrioMatch(self):
        """ There is admin code that depends on these being equal. """
        self.assertEqual(Task.PRIO_LOW, RecurringTaskTemplate.PRIO_LOW)
        self.assertEqual(Task.PRIO_MED, RecurringTaskTemplate.PRIO_MED)
        self.assertEqual(Task.PRIO_HIGH, RecurringTaskTemplate.PRIO_HIGH)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =]

class TestViews(TestCase):

    def setUp(self):

        self.arbitrary_token_b64 = 'S2s8DNreTH2R92Dfhzcdhp1aGVV1X0wj'
        self.arbitrary_token_md5 = 'acd706cdada4cbaa339cae813a25c30f'
        self.user = User.objects.create_superuser(username='admin', password='123', email='')
        self.member = Member.objects.first()
        self.member.membership_card_md5 = self.arbitrary_token_md5
        self.member.save()
        self.rt = RecurringTaskTemplate.objects.create(
            short_desc="Test Task",
            max_work=timedelta(hours=1.5),
            work_start_time=time(18, 00),
            work_duration=timedelta(hours=1.5),
            start_date=date.today(),
            repeat_interval=1,
        )
        self.rt.full_clean()
        TemplateEligibleClaimant2.objects.create(template=self.rt, member=self.member)
        self.rt.create_tasks(max_days_in_advance=3)

        self.task = Task.objects.first()
        tn = TaskNote.objects.create(task=self.task, author=self.member, content="spam", status=TaskNote.INFO)
        tn.full_clean()
        self.nag = Nag.objects.create(who=self.member, auth_token_md5=self.arbitrary_token_md5)
        self.nag.full_clean()
        self.nag.tasks.add(self.task)
        self.claim = Claim.objects.create(
            status=Claim.STAT_CURRENT,
            claiming_member=self.member,
            claimed_task=self.task,
            claimed_duration=timedelta(hours=1.5),
            claimed_start_time=self.task.work_start_time,
        )
        self.claim.full_clean()
        self.nag.claims.add(self.claim)
        self.work = Work.objects.create(
            claim=self.claim,
            work_date=datetime.today(),
            work_duration=timedelta(hours=1.5))
        self.work.full_clean()
        self.worknote = WorkNote.objects.create(
            author=self.member,
            content="Well done!",
            work=self.work)
        self.worknote.full_clean()
        self.fact = RequestFactory()

    def test_worker(self):
        self.assertNotEqual(self.user.member, None)
        self.assertNotEqual(self.member.worker, None)

    _MODEL_CLASSNAMES = [
        "RecurringTaskTemplate",
        "Task",
        "Nag",
        "Claim",
        "Work",
        "TaskNote",
        "Worker",
    ]

    def test_admin_views(self):  # TODO: Generalize this and move it to xerocraft.tests

        for model_classname in self._MODEL_CLASSNAMES:

            model_cls = locate("tasks.models.%s" % model_classname)
            admin_cls = locate("tasks.admin.%sAdmin" % model_classname)
            admin_inst = admin_cls(model_cls, site)
            model_inst = model_cls.objects.first()
            assert model_inst is not None, "Test didn't create instances of %s" % model_classname
            url = "/admin/tasks/%s/" % model_classname.lower()

            # Test the list view:
            request = self.fact.get(url)
            request.user = self.user
            response = admin_inst.changelist_view(request)
            self.assertEqual(response.status_code, 200, "Admin view failure: %s" % url)

            # Test the detail view:
            request = self.fact.get(url)
            request.user = self.user
            response = admin_inst.change_view(request, str(model_inst.pk))
            self.assertEqual(response.status_code, 200, "Admin view failure: %s" % url)

    def test_nag_offer_views(self):
        client = Client()

        url = reverse('task:offer-task', args=[str(self.task.pk), self.arbitrary_token_b64])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # The claim and work were required for previous tests, but delete them because following will recreate them.
        self.work.delete()
        self.claim.delete()
        self.assertEqual(len(self.task.claimant_set(Claim.STAT_CURRENT)), 0)
        response = client.post(url, {'hours':"01:30:00"})
        # On success, response will redirect to next in the nag handling process.
        kwargs = {'task_pk':str(self.task.pk), 'auth_token':self.arbitrary_token_b64}
        self.assertRedirects(
            response,
            reverse('task:offer-more-tasks', kwargs=kwargs),
            302,  # POST to offer-task will respond with a redirect to offer-more-tasks
            302   # Because there are no other tasks on same day, offer-more-tasks will redirect to next in chain.
        )
        self.assertEqual(len(self.task.claimant_set(Claim.STAT_CURRENT)), 1)

        # Add more tasks so there is one on the same day of week and retry the previous.
        # This time it shouldn't redirect.
        Claim.objects.first().delete()  # Will be reclaiming the task again in this step.
        self.rt.create_tasks(max_days_in_advance=8)
        response = client.post(url, {'hours':"01:30:00"})
        self.assertRedirects(
            response,
            reverse('task:offer-more-tasks', kwargs=kwargs),
            302,  # POST to offer-task will respond with a redirect to offer-more-tasks
            200   # Because there ARE other tasks on same day, offer-more-tasks will not redirect.
        )
        self.assertTrue(self.task.is_fully_claimed)

        response = client.post(
            reverse('task:offer-more-tasks', kwargs=kwargs),
            {'tasks': [str(Task.objects.last().pk)]}
        )
        self.assertTrue(response.status_code, 200)
        self.assertEqual(len(Claim.objects.all()), 2)

        response = client.get(
            reverse('task:offers-done', kwargs={'auth_token': self.arbitrary_token_b64})
        )
        self.assertTrue(response.status_code, 200)

        response = client.get(
            reverse('task:member-calendar', kwargs={'token':self.arbitrary_token_b64})
        )
        self.assertTrue(response.status_code, 200)

    def test_calendar_views(self):

        t = Task.objects.create(
            short_desc="TCV",
            max_work=timedelta(hours=2),
            max_workers=1,
            work_start_time=time(19,00,00),
            work_duration=timedelta(hours=2),
            scheduled_date=date.today(),
            orig_sched_date=date.today(),
        )
        t.full_clean()

        expected_words = ["TCV","BEGIN","SUMMARY","DTSTART","DTEND","DTSTAMP","UID","DESCRIPTION","URL","END"]

        client = Client()
        url = reverse('task:ops-calendar')
        response = client.get(url)
        for word in expected_words:
            self.assertContains(response, word)

        url = reverse('task:ops-calendar-unstaffed')
        response = client.get(url)
        for word in expected_words:
            self.assertContains(response, word)

        c = Claim.objects.create(
            claimed_task=t,
            claiming_member=self.member,
            claimed_duration=t.work_duration,
            claimed_start_time=t.work_start_time,
            status=Claim.STAT_CURRENT,
        )
        c.full_clean()
        t.claim_set.add(c)

        url = reverse('task:ops-calendar-provisional')
        response = client.get(url)
        for word in expected_words:
            self.assertContains(response, word)

        # verifying the claim takes it from being "provisionally staffed" to "staffed"
        c.date_verified = datetime.today()
        c.save()

        url = reverse('task:ops-calendar-staffed')
        response = client.get(url)
        for word in expected_words:
            self.assertContains(response, word)

        url = reverse('task:kiosk-task-details', args=[t.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TCV")

        url = reverse('task:cal-task-details', args=[t.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TCV")


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class TestOpsCalendarSpa(TestCase):

    def test_anonymous_user(self):
        client = Client()
        url = reverse('task:ops-calendar-spa')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class RunSchedAndNagCmds(TestCase):
    """It's best to run scheduletasks before nag, so this test does both."""

    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='123', email='test@example.com')
        member = self.user.member
        member.worker.should_nag = True
        member.worker.save()

        self.rt = RecurringTaskTemplate.objects.create(
            short_desc="Sched and Nag Cmd Test",
            max_work=timedelta(hours=1.5),
            max_workers=1,
            work_start_time=time(19, 0, 0),
            work_duration=timedelta(2),
            start_date=date.today(),
            repeat_interval=1,
            should_nag=True,
        )
        self.rt.full_clean()

        TemplateEligibleClaimant2.objects.create(template=self.rt, member=member)

    def test_run_nagger(self):
        management.call_command("scheduletasks", "2")
        management.call_command("nag")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(Nag.objects.all()), 1)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class RunEmailWMTD(TestCase):

    def test_database_validity(self):

        self.user = User.objects.create_superuser(username='JoeSmith', password='123', email='somebody@email.com')
        self.member = self.user.member

        self.task = Task.objects.create(
            short_desc="Do Something",
            max_work=timedelta(hours=1.5),
            work_start_time=time(18, 00),
            work_duration=timedelta(hours=1.5),
            scheduled_date=date.today(),
            orig_sched_date=date.today(),
        )  # type: Task
        self.task.full_clean()

        self.claim = Claim.objects.create(
            status=Claim.STAT_CURRENT,
            claiming_member=self.member,
            claimed_task=self.task,
            claimed_duration=timedelta(hours=1.5),
            claimed_start_time=self.task.work_start_time,
        )
        self.claim.full_clean()

        self.member.worker.should_report_work_mtd = True
        self.member.worker.save()
        management.call_command("email_statements")
        self.assertEqual(len(mail.outbox), 0)  # Beacuse no work has been completed yet.

        self.work = Work.objects.create(
            claim=self.claim,
            work_date=datetime.today(),
            work_duration=timedelta(hours=1.5),
            witness=self.member
        )
        self.work.full_clean()

        self.member.worker.should_report_work_mtd = False
        self.member.worker.save()
        management.call_command("email_statements")
        self.assertEqual(len(mail.outbox), 0)  # Because the worker doesn't want updates.

        self.member.worker.should_report_work_mtd = True
        self.member.worker.save()
        management.call_command("email_statements")
        self.assertEqual(len(mail.outbox), 1)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

today = date.today()
oneday = timedelta(hours=24)
yesterday = today - oneday
tomorrow = today + oneday
now = datetime.now()
onehour = timedelta(hours=1)
halfhour = timedelta(minutes=30)
fourhours = timedelta(hours=4)
zerodur = timedelta(0)


class TestWindowedObject(TestCase):

    def setUp(self):
        self.t = Task.objects.create(
            short_desc="TCV",
            max_work=timedelta(hours=2),
            max_workers=1
        )
        self.t.full_clean()

    def test_task_and_ABC(self):

        def caselet(result, start=None, dur=None, sched=None, dead=None, start_leeway=zerodur, end_leeway=zerodur):
            self.t.work_start_time = start
            self.t.work_duration = dur
            self.t.scheduled_date = sched
            self.t.deadline = dead
            # No need to self.t.save() during this test.
            self.assertEqual(self.t.in_window_now(start_leeway, end_leeway), result)

        caselet(True) # start, dur, sched, and dead all None.

        caselet(False, sched=yesterday)
        caselet(True, sched=today)
        caselet(False, sched=tomorrow)

        caselet(False, dead=yesterday)
        caselet(True, dead=today)
        caselet(True, dead=tomorrow)

        caselet(True, start=(now-halfhour).time(), dur=fourhours)
        caselet(False, start=(now+onehour).time(), dur=fourhours)
        caselet(True, start=(now+halfhour).time(), dur=fourhours, start_leeway=-onehour)  # NOTE: *Minus* onehour

        caselet(False, sched=yesterday, start=(now-halfhour).time(), dur=fourhours)
        caselet(False, sched=yesterday, start=(now+onehour).time(), dur=fourhours)
        caselet(False, sched=yesterday, start=(now+halfhour).time(), dur=fourhours, start_leeway=-onehour)  # NOTE: *Minus* onehour

        caselet(True, sched=today, start=(now-halfhour).time(), dur=fourhours)
        caselet(False, sched=today, start=(now+onehour).time(), dur=fourhours)
        caselet(True, sched=today, start=(now+halfhour).time(), dur=fourhours, start_leeway=-onehour)  # NOTE: *Minus* onehour

        caselet(False, dead=yesterday, start=(now-halfhour).time(), dur=fourhours)
        caselet(False, dead=yesterday, start=(now+onehour).time(), dur=fourhours)
        caselet(False, dead=yesterday, start=(now+halfhour).time(), dur=fourhours, start_leeway=-onehour)  # NOTE: *Minus* onehour

        caselet(True, dead=today, start=(now-halfhour).time(), dur=fourhours)
        caselet(False, dead=today, start=(now+onehour).time(), dur=fourhours)
        caselet(True, dead=today, start=(now+halfhour).time(), dur=fourhours, start_leeway=-onehour)  # NOTE: *Minus* onehour

    def test_claim_imp(self):

        user = User.objects.create_user(username='claimer', password='123', email='')
        member = Member.objects.first()

        self.t.work_start_time = now.time()
        self.t.work_duration = fourhours
        self.t.scheduled_date = today
        self.t.deadline = tomorrow

        claim = Claim.objects.create(
            status=Claim.STAT_CURRENT,
            claiming_member=member,
            claimed_task=self.t,
            claimed_start_time=now,
            claimed_duration=onehour)
        claim.full_clean()

        self.assertEqual(claim.window_start_time(), now.time())
        self.assertEqual(claim.window_duration(), onehour)
        self.assertEqual(claim.window_sched_date(), self.t.scheduled_date)
        self.assertEqual(claim.window_deadline(), self.t.deadline)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# TEST REST APIs

class TestRestApi_Tasks(TestCase):

    def setUp(self):

        self.claim_list_uri = reverse("task:claim-list")
        self.task_list_uri = reverse("task:task-list")
        self.member_list_uri = reverse("memb:member-list")

        # Person who will make the REST API call
        caller = User.objects.create(username='caller')
        caller.set_password("pw4caller")
        caller.save()
        caller.clean()
        caller.member.clean()
        self.caller = caller.member

        # Some other person who will create tasks
        other = User.objects.create(username='other',first_name="fn4other", last_name="ln4other")
        other.set_password("pw4other")
        other.save()
        other.clean()
        other.member.clean()
        self.other = other.member

        # The caller's "browser"
        self.factory = APIRequestFactory()
        logged_in = self.client.login(username="caller", password="pw4caller")
        self.assertTrue(logged_in)

        # Data for a task
        self.task_data = {
            'short_desc': "Test",
            'max_work': timedelta(hours=2),
            'max_workers': 1,
            'work_start_time': datetime.now().time(),
            'work_duration': timedelta(hours=2),
            'scheduled_date': date.today(),
            'orig_sched_date': date.today(),
        }

        self.claim_data = {
            "status": Claim.STAT_CURRENT,
            "claiming_member": "{}{}/".format(self.member_list_uri, self.caller.pk),
            "claimed_task": None,  # Must provide
            "claimed_start_time": "19:00:00",
            "claimed_duration": "02:00:00",
        }

    def test_need_creds_to_create_task(self):
        view = restapi.views.TaskViewSet.as_view({'post': 'create'})
        request = self.factory.post(self.task_list_uri)
        response = view(request)
        # Why am I getting different status codes in dev vs jenkins (401 vs 403)?
        self.assertGreater(response.status_code, 400)

    def test_can_create_and_read_task(self):

        view = restapi.views.TaskViewSet.as_view({'post': 'create'})
        request = self.factory.post(self.task_list_uri, self.task_data)
        force_authenticate(request, self.caller.auth_user)
        response = view(request)
        self.assertEqual(response.status_code, 201)  # 201 = Created
        pk = response.data['id']

        uri = reverse("task:task-detail", args=[pk])
        request = self.factory.get(uri)
        force_authenticate(request, self.caller.auth_user)
        view = restapi.views.TaskViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=pk)
        self.assertEqual(response.status_code, 200)

    # Decided against this b/c of ops calendar use-case. User wants to see all tasks, not just theirs.
    # def test_list_only_my_tasks(self):
    #
    #     # Other person creates a task
    #     self.task_data["owner"] = self.other
    #     Task.objects.create(**self.task_data)
    #
    #     # "I" shouldn't see it on the API's list
    #     request = self.factory.get(self.task_list_uri)
    #     force_authenticate(request, self.caller.auth_user)
    #     view = restapi.views.TaskViewSet.as_view({'get': 'list'})
    #     response = view(request)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(len(response.data["results"]), 0)
    #
    #     # "I" create a task
    #     self.task_data["owner"] = self.caller
    #     self.task_data["short_desc"] = "Another task"
    #     Task.objects.create(**self.task_data)
    #
    #     # There are now two tasks in the system
    #     self.assertEqual(Task.objects.count(), 2)
    #
    #     # "I" should now see ONE task on the API's list
    #     request = self.factory.get(self.task_list_uri)
    #     force_authenticate(request, self.caller.auth_user)
    #     view = restapi.views.TaskViewSet.as_view({'get': 'list'})
    #     response = view(request)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(len(response.data["results"]), 1)

    def test_can_claim_task_if_eligible(self):

        # Somebody creates a task that caller is eligible to work:
        t = Task.objects.create(**self.task_data)  # type: Task
        t.save()
        t.clean()

        EligibleClaimant2.objects.create(task=t, member=self.caller)

        view = restapi.views.ClaimViewSet.as_view({'post': 'create'})
        self.claim_data["claimed_task"] = "{}{}/".format(self.task_list_uri, t.pk)
        request = self.factory.post(self.claim_list_uri, self.claim_data, format='json')
        force_authenticate(request, self.caller.auth_user)
        response = view(request)
        self.assertEqual(response.status_code, 201)  # Created

    def test_CANNOT_claim_task_if_NOT_eligible(self):

        # Somebody creates a task that caller is NOT eligible to work:
        t = Task.objects.create(**self.task_data)
        t.clean()

        view = restapi.views.ClaimViewSet.as_view({'post': 'create'})
        self.claim_data["claimed_task"] = "{}{}/".format(self.task_list_uri, t.pk)
        request = self.factory.post(self.claim_list_uri, self.claim_data, format='json')
        force_authenticate(request, self.caller.auth_user)
        response = view(request)
        self.assertEqual(response.status_code, 403)  # Forbidden


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# Test Snippets

class TestSnippets(TestCase):

    snippet1_name = "foo"
    snippet1_content = "foo foo foo"

    snippet2_name = "bar"
    snippet2_content = "bar bar bar"

    def setUp(self):
        Snippet.objects.create(
            name=TestSnippets.snippet1_name,
            description="for testing purposes",
            text=TestSnippets.snippet1_content)
        Snippet.objects.create(
            name=TestSnippets.snippet2_name,
            description="for testing purposes",
            text=TestSnippets.snippet2_content)

    def test_zero_refs(self):
        test_string = "This is a test of expansion."
        result = Snippet.expand(test_string)
        self.assertEqual(result, test_string)

    def test_one_ref(self):
        test_string = "This is a test of %s expansion."
        unexpanded = test_string % "{{%s}}" % TestSnippets.snippet1_name
        expected_expansion = test_string % TestSnippets.snippet1_content
        result = Snippet.expand(unexpanded)
        self.assertEqual(result, expected_expansion)

    def test_two_refs(self):
        test_string = "This is a %s test of %s expansion."
        unexpanded = test_string % ("{{%s}}", "{{%s}}") % (TestSnippets.snippet1_name, TestSnippets.snippet2_name)
        expected_expansion = test_string % (TestSnippets.snippet1_content, TestSnippets.snippet2_content)
        result = Snippet.expand(unexpanded)
        self.assertEqual(result, expected_expansion)

    def test_bad_ref(self):
        test_string = "This is a test of %s expansion."
        unexpanded = test_string % "{{%s}}" % "badname"
        expected_expansion = test_string % Snippet.BAD_SNIPPET_REF_STR
        result = Snippet.expand(unexpanded)
        self.assertEqual(result, expected_expansion)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# Notifications

class TestNotifications(TestCase):

    def setUp(self):
        # Worker
        self.worker_user = User.objects.create_user(username='worker', password='123', email='')  # type User
        self.worker_member = self.worker_user.member
        # Manager
        self.manager_user = User.objects.create_user(username=USER_VOLUNTEER, password='123', email='')  # type User
        self.manager_member = self.manager_user.member
        notify.MOST_RECENT_MEMBER = None
        notify.MOST_RECENT_TITLE = None
        notify.MOST_RECENT_MESSAGE = None

    def test_testability(self):  # TODO: This should be in members.tests
        title = "TITLE"
        message = "MESSAGE"
        notify(self.manager_member, title, message)
        self.assertEqual(notify.MOST_RECENT_MEMBER, self.manager_member)
        self.assertEqual(notify.MOST_RECENT_TITLE, title)
        self.assertEqual(notify.MOST_RECENT_MESSSAGE, message)

    def test_arrival_of_scheduled_worker(self):
        VisitEvent.objects.all().delete()
        tz = timezone.get_current_timezone()
        start_dt = datetime.now() + timedelta(minutes=15)  # type: datetime
        start_dt = tz.localize(start_dt)  # type: datetime
        task = Task.objects.create(
            owner=self.manager_member,
            priority=Task.PRIO_HIGH,
            short_desc="Test Task",
            work_start_time=start_dt.time(),
            max_work=timedelta(hours=2),
            scheduled_date=start_dt.date(),
            orig_sched_date = start_dt.date(),
        )
        task.clean()
        claim = Claim.objects.create(
            claimed_task=task,
            claiming_member=self.worker_member,
            claimed_start_time=start_dt.time(),
            claimed_duration=timedelta(hours=1),
            status=Claim.STAT_CURRENT,
        )
        claim.clean()
        VisitEvent.objects.create(
            who=self.worker_member,
            event_type=VisitEvent.EVT_ARRIVAL
        )
        self.assertEqual(notify.MOST_RECENT_MEMBER, self.manager_member)
        self.assertTrue("Arrived" in notify.MOST_RECENT_TITLE)
        self.assertTrue("Scheduled" in notify.MOST_RECENT_MESSSAGE)


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# Miscellaneous

class TestScheduledReceptionist(TestCase):

    def setUp(self):
        user = User.objects.create_user(username='admin', password='123', email='')  # type User
        self.member = user.member

        self.task = Task.objects.create(
            short_desc="Open, Staff, Close",
            max_work=timedelta(hours=2),
            max_workers=1,
            work_start_time=time(17,0,0),
            work_duration=timedelta(hours=2),
            scheduled_date=date.today(),
            orig_sched_date=date.today(),
        )
        self.task.full_clean()

        self.claim = Claim.objects.create(
            status=Claim.STAT_CURRENT,
            claiming_member=self.member,
            claimed_task=self.task,
            claimed_duration=timedelta(hours=1.5),
            claimed_start_time=self.task.work_start_time,
        )
        self.claim.full_clean()

    def test_cases(self):
        cases = [
            (None, -1*ONEDAY),
            (None, -1*ONEHOUR),
            (self.member, ONEHOUR),
            (None, 3*ONEHOUR),
            (None, ONEDAY)
        ]
        for result, delta in cases:
            with freeze_time(self.task.window_start_datetime() + delta):
                self.assertEqual(Worker.scheduled_receptionist(), result)


class TestMisc(TestCase):

    def test_with_dbcheck_command(self):
        call_command('addmissingworkers')
