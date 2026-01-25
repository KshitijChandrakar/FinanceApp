import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import *
import pandas as pd
from django.db import transaction
from django.db.models import fields
import pandas as pd

# models_columns.py
from django.apps import apps
from decimal import Decimal
from io import BytesIO

import pandas as pd
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Category, Transaction


def create_excel_response(request):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # 1. Export Category data
        categories = Category.objects.all()
        if categories.exists():
            df_categories = pd.DataFrame(list(categories.values()))
            # Format column names
            # df_categories.columns = [col.replace('_', ' ').title() for col in df_categories.columns]
            # Write to Excel with auto-width columns
            df_categories.to_excel(writer, sheet_name="Category", index=False)

            # Auto-adjust column widths for Categories sheet
            worksheet_cat = writer.sheets["Category"]
            for i, col in enumerate(df_categories.columns):
                column_width = (
                    max(df_categories[col].astype(str).map(len).max(), len(col)) + 2
                )
                worksheet_cat.column_dimensions[chr(65 + i)].width = min(
                    column_width, 50
                )

        # 2. Export Transaction data
        transactions = Transaction.objects.all()
        if transactions.exists():
            trans_values = list(transactions.values())
            df_transactions = pd.DataFrame(trans_values)

            # Handle datetime field
            if "datetime" in df_transactions.columns:
                df_transactions["datetime"] = pd.to_datetime(
                    df_transactions["datetime"]
                )
                if df_transactions["datetime"].dt.tz is not None:
                    df_transactions["datetime"] = df_transactions[
                        "datetime"
                    ].dt.tz_localize(None)

                # Format datetime for better readability
                df_transactions["datetime"] = df_transactions["datetime"].dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            # Format column names
            # df_transactions.columns = [col.replace('_', ' ').title() for col in df_transactions.columns]
            # Write to Excel
            df_transactions.to_excel(writer, sheet_name="Transaction", index=False)

            # Auto-adjust column widths for Transactions sheet
            worksheet_trans = writer.sheets["Transaction"]
            for i, col in enumerate(df_transactions.columns):
                column_width = (
                    max(df_transactions[col].astype(str).map(len).max(), len(col)) + 2
                )
                worksheet_trans.column_dimensions[chr(65 + i)].width = min(
                    column_width, 50
                )

    # Prepare the HTTP response
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="budget_data_export.xlsx"'

    return response


def export_to_json(request):
    # Get all categories
    categories = Category.objects.all()

    # Create the nested structure you want
    result = {}

    for item in categories:
        total_sum = (
            float(item.total_sum)
            if isinstance(item.total_sum, Decimal)
            else item.total_sum
        )

        if item.category not in result:
            result[item.category] = {}

        # Add subcategory and total_sum to the category
        result[item.category][item.subcategory] = total_sum

    return JsonResponse(result, safe=False, json_dumps_params={"indent": 2})


def get_model_columns():
    """Get expected columns for all models in the 'ui' app."""
    expected = {}
    app_label = "ui"

    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        raise ValueError(f"App '{app_label}' not found in INSTALLED_APPS")

    for model in app_config.get_models():
        name = model.__name__
        # Get all concrete, non-auto-created fields
        cols = [
            f.name
            for f in model._meta.get_fields()
            if f.concrete and not (f.auto_created or f.many_to_many)
        ]
        expected[name] = sorted(cols)  # Sort for consistent comparison

    return expected


# excel_importer.py


def import_excel_strict(file):
    EXPECTED_COLUMNS = get_model_columns()

    try:
        xl = pd.ExcelFile(file)
    except Exception as e:
        raise ValueError(f"Failed to open Excel file: {str(e)}")

    imported_data = {}
    sheet_names = xl.sheet_names

    for sheet, expected_cols in EXPECTED_COLUMNS.items():
        if sheet not in sheet_names:
            # Case-insensitive check
            sheet_lower = sheet.lower()
            matched = [s for s in sheet_names if s.lower() == sheet_lower]
            if matched:
                sheet = matched[0]  # Use the actual sheet name
            else:
                raise ValueError(f"Required sheet '{sheet}' missing!")

        try:
            df = pd.read_excel(
                xl, sheet_name=sheet, dtype=str
            )  # Read as strings initially
        except Exception as e:
            raise ValueError(f"Failed to read sheet '{sheet}': {str(e)}")

        # Clean column names (strip whitespace)
        df.columns = df.columns.astype(str).str.strip()
        actual_cols = sorted([str(col).lower() for col in df.columns])
        expected_cols_sorted = sorted([str(col).lower() for col in expected_cols])
        actual_set = sorted(set(actual_cols) - {"id"})
        expected_set = sorted(set(expected_cols_sorted))
        if actual_set != expected_set:
            actual_set = set(actual_cols)
            expected_set = set(expected_cols_sorted)

            extra = sorted(list(actual_set - expected_set))
            missing = sorted(list(expected_set - actual_set))

            err_msg = f"Sheet '{sheet}' column validation failed!"
            if extra:
                err_msg += f" Extra columns: {extra}"
            if missing:
                err_msg += f" Missing columns: {missing}"

            raise ValueError(err_msg)

        imported_data[sheet] = df

    return imported_data


def delete_rows(df, model, batch_size=1000):
    """
    Delete rows in batches for better performance with large datasets.
    For Category model, matches on composite key: category + subcategory.
    Optimized version using database operations.
    """
    from django.db import transaction
    from django.db.models import Q

    # Ensure the DataFrame has the required columns
    required_columns = ["category", "subcategory"]
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"DataFrame must contain columns: {required_columns}")

    # Clean and prepare DataFrame data
    df["category"] = df["category"].astype(str).str.strip()
    df["subcategory"] = df["subcategory"].astype(str).str.strip()

    # Create a list of Q objects for rows that SHOULD exist
    q_filters = Q()
    for _, row in df.iterrows():
        q_filters |= Q(category=row["category"], subcategory=row["subcategory"])

    # Get rows that are NOT in the DataFrame
    # This is the inverse: rows that don't match any of the combinations in df
    if q_filters:
        # Note: This can be inefficient for very large df, but is database-optimized
        qs_to_delete = model.objects.exclude(q_filters)
    else:
        # If df is empty, delete everything
        qs_to_delete = model.objects.all()

    # Get count before deletion
    count_before = qs_to_delete.count()

    # Delete in batches using iterator() for memory efficiency
    deleted_count = 0
    while True:
        batch_ids = list(qs_to_delete.values_list("id", flat=True)[:batch_size])
        if not batch_ids:
            break

        deleted, _ = model.objects.filter(id__in=batch_ids).delete()
        deleted_count += deleted

    return deleted_count


def sync_dataframes_to_models(dataframes_dict, model_mapping):
    """
    Sync pandas DataFrames with Django models.

    Args:
        dataframes_dict: dict of {model_name: dataframe}
        model_mapping: dict of {model_name: DjangoModelClass}

    Returns:
        dict: Results summaryet
    """
    results = {}

    with transaction.atomic():
        for model_name, df in dataframes_dict.items():
            if model_name not in model_mapping:
                continue

            Model = model_mapping[model_name]
            created = updated = skipped = 0
            df.columns = [i.lower() for i in df.columns]
            # Get model's field names for dataframe alignment
            model_fields = [f.name for f in Model._meta.fields if not f.primary_key]
            df = df[model_fields]
            # Handle each row in dataframe
            deleted = delete_rows(df, Model)
            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # Filter row data to match model fields
                # Determine identifier field (first unique field or use 'id')

                obj, is_created = Model.objects.update_or_create(
                    category=row_dict[
                        "category"
                    ],  # Lookup fields (for finding existing record)
                    subcategory=row_dict["subcategory"],
                    defaults=row_dict,  # Fields to update/create
                )

                if is_created:
                    created += 1
                else:
                    updated += 1
            results[model_name] = {
                "created": created,
                "updated": updated,
                "deleted": deleted,
                "total": len(df),
            }

    return results


# views.py


@csrf_exempt
@require_POST
def upload_excel(request):
    if "file" not in request.FILES:
        return JsonResponse({"status": "error", "msg": "No file provided"}, status=400)

    file = request.FILES["file"]

    # Validate file extension
    if not file.name.endswith((".xlsx", ".xls")):
        return JsonResponse(
            {"status": "error", "msg": "Only Excel files are allowed"}, status=400
        )

    try:
        data = import_excel_strict(file)
        results = sync_dataframes_to_models(
            data, {"Category": Category, "Transaction": Transaction}
        )
        print(results)

        return JsonResponse(
            {
                "status": "ok",
                "msg": "Import successful",
                "sheets_imported": list(data.keys()),
                "row_counts": {sheet: len(df) for sheet, df in data.items()},
            }
        )
    except ValueError as err:
        return JsonResponse({"status": "error", "msg": str(err)}, status=400)
    except Exception as err:
        # Log unexpected errors
        return JsonResponse({"status": "error", "msg": err}, status=500)
