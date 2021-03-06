from django.conf.urls import url, include
from . import views
from rest_framework import routers

app_name = "books"  # This is the app namespace not the app name.

router = routers.DefaultRouter()
router.register(r'sales', views.SaleViewSet)
router.register(r'sale-notes', views.SaleNoteViewSet)
router.register(r'monetary-donations', views.MonetaryDonationViewSet)
router.register(r'other-items', views.OtherItemViewSet)
router.register(r'other-item-types', views.OtherItemTypeViewSet)

urlpatterns = [

    # url(r'^cumulative-vs-date-chart/$', views.cumulative_vs_date_chart, name='cumulative-vs-date-chart'),
    # url(r'^cumulative-vs-date-chart/2/$', views.cumulative_vs_date_chart, name='cumulative-vs-date-chart'),
    url(r'^cumulative-rev-exp-chart/$', views.revenues_and_expenses_from_journal, name='cumulative-rev-exp-chart'),
    url(r'^cashonhand-vs-time-chart/$', views.cashonhand_vs_time_chart, name='cashonhand-vs-time-chart'),
    url(r'^account-browser/$', views.account_browser, name='account-browser'),
    url(r'^items-needing-attn/$', views.items_needing_attn, name='items-needing-attn'),
    url(r'^account-history/(?P<account_pk>[0-9]+)_(?P<begin_date>[0-9]+)_(?P<end_date>[0-9]+)/$', views.account_history, name='account-history-in-range'),
    url(r'^account-history/(?P<account_pk>[0-9]+)/$', views.account_history, name='account-history'),

    # Webhooks for Payment Processors
    url(r'^squareup/$', views.squareup_webhook, name='squareup-webhook'),

    # DJANGO REST FRAMEWORK API
    url(r'^', include(router.urls)),
]
