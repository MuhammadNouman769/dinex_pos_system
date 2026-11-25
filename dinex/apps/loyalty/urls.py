from django.urls import path
from apps.loyalty import views as v

urlpatterns = [
    path("settings/", v.LoyaltySettingsView.as_view()),
    path("lookup/", v.LookupView.as_view()),
    path("reminders/send/", v.SendRemindersView.as_view()),
]
