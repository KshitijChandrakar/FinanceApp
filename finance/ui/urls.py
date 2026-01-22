from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "api/category-summary/", views.category_summary_api, name="category_summary_api"
    ),
    path("api/category", views.get_categories_json, name="get_categories"),
    path("api/transaction-add", views.transaction_add, name="transaction_add"),
    # path('transactions/', views.transaction_list, name='transaction_list'),
    path("api/transactions/", views.transaction_api, name="transaction_api"),
]
