from django.urls import path

from . import Excel, Export, views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "api/category-summary/", views.category_summary_api, name="category_summary_api"
    ),
    path("api/category", views.get_categories_json, name="get_categories"),
    path("api/transaction-add", views.transaction_add, name="transaction_add"),
    path("api/transactions/", views.transaction_api, name="transaction_api"),
    path("api/typst-json/", Export.export_to_json, name="export_to_json"),
    path("api/excel-export/", Export.create_excel_response, name="excel_export"),
    path("api/excel-import/", Export.upload_excel, name="excel_import"),
]
