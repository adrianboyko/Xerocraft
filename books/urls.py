from django.conf.urls import url, include
from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'sales', views.SaleViewSet)
router.register(r'sale-notes', views.SaleNoteViewSet)
router.register(r'donations', views.DonationViewSet)
router.register(r'donation-notes', views.DonationNoteViewSet)
router.register(r'physical-donations', views.PhysicalDonationViewSet)
router.register(r'monetary-donations', views.MonetaryDonationViewSet)

urlpatterns = [

    # DJANGO REST FRAMEWORK API
    url(r'^', include(router.urls)),
]

