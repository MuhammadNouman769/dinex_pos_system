from django.urls import path
from apps.customers.views.customer_view import (
    CustomerListCreateView,
    CustomerRetrieveUpdateDeleteView,
)

urlpatterns = [
    path('', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('<int:pk>/', CustomerRetrieveUpdateDeleteView.as_view(), name='customer-detail'),
]