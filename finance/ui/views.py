import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.core.serializers import serialize
from django.db.models import DecimalField, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import *


def home(request):
    # Context dictionary - data passed to template
    context = {}

    # Render the template with context
    return render(request, "ui/home.html", context)


@require_GET
def category_summary_api(request):
    # Query all categories
    categories = Category.objects.all().order_by("category", "subcategory")

    # Calculate grand total in a single query
    grand_total_result = categories.aggregate(
        total=Sum("total_sum", output_field=DecimalField())
    )
    grand_total = grand_total_result["total"] or Decimal("0.00")

    # Build the categories dictionary
    categories_dict = {}

    for cat in categories:
        main_cat = cat.category
        sub_cat = cat.subcategory

        if main_cat not in categories_dict:
            categories_dict[main_cat] = {}

        categories_dict[main_cat][sub_cat] = float(cat.total_sum)

    # Prepare response
    data = {"categories": categories_dict, "grand_total": float(grand_total)}
    print(data)
    return JsonResponse(data)


def categories():
    category_pairs = Category.objects.values_list("category", "subcategory").distinct()

    # Organize into the required structure
    categories_dict = {}

    for category, subcategory in category_pairs:
        if category not in categories_dict:
            categories_dict[category] = []
        categories_dict[category].append(subcategory)
    return categories_dict


def get_categories_json(request):
    # Query to get all unique category-subcategory pairs
    # Using values_list to get distinct pairs
    categories_dict = categories()
    return JsonResponse(categories_dict)


@csrf_exempt
@require_POST
def transaction_add(request):
    """
    Handle POST request to add a new transaction.
    Expected JSON data: {
        "category": "category_name",
        "subcategory": "subcategory_name",
        "amount": 123.45
    }
    """
    try:
        # Parse JSON data from request
        data = json.loads(request.body)

        # Extract and validate required fields
        category = data.get("category")
        subcategory = data.get("subcategory")
        amount_str = data.get("amount")

        # Check if all required fields are present
        if not category:
            return JsonResponse({"error": "Category is required"}, status=400)

        if not subcategory:
            return JsonResponse({"error": "Subcategory is required"}, status=400)

        if not amount_str:
            return JsonResponse({"error": "Amount is required"}, status=400)

        # Validate amount is positive
        try:
            # Convert to Decimal for precise monetary calculation
            amount = Decimal(str(amount_str))

            # Check if amount is positive
            if amount <= Decimal("0"):
                return JsonResponse(
                    {"error": "Amount must be a positive number"}, status=400
                )

        except (InvalidOperation, ValueError, TypeError):
            return JsonResponse(
                {"error": "Invalid amount format. Please provide a valid number."},
                status=400,
            )

        # Get categories dictionary to validate category/subcategory
        categories_dict = categories()

        # Validate category exists
        if category not in categories_dict:
            return JsonResponse(
                {"error": f'Category "{category}" does not exist'}, status=400
            )

        # Validate subcategory exists under the specified category
        if subcategory not in categories_dict[category]:
            return JsonResponse(
                {
                    "error": f'Subcategory "{subcategory}" does not exist under category "{category}"'
                },
                status=400,
            )

        # Create and save the transaction
        transaction = Transaction(
            datetime=datetime.now(),  # Auto-generate current datetime
            category=category,
            subcategory=subcategory,
            amount=amount,
        )

        transaction.save()

        # Return success response
        return JsonResponse(
            {
                "success": True,
                "message": "Transaction added successfully",
                "transaction": {
                    "id": transaction.id,
                    "datetime": transaction.datetime.isoformat(),
                    "category": transaction.category,
                    "subcategory": transaction.subcategory,
                    "amount": str(transaction.amount),
                },
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    except Exception as e:
        # Log the error for debugging
        # logger.error(f"Error adding transaction: {str(e)}")

        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


# API view for JSON data
@require_GET
def transaction_api(request):
    # Get query parameters
    page = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 5)

    # Get all transactions ordered by date (recent first)
    transactions = Transaction.objects.all().order_by("-datetime")

    # Pagination
    paginator = Paginator(transactions, per_page)

    try:
        page_number = int(page)
        if page_number < 1:
            page_number = 1
        elif page_number > paginator.num_pages:
            page_number = paginator.num_pages
    except ValueError:
        page_number = 1

    page_obj = paginator.get_page(page_number)

    # Prepare data for JSON response
    data = {
        "count": paginator.count,
        "num_pages": paginator.num_pages,
        "current_page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "transactions": [],
    }

    for transaction in page_obj.object_list:
        data["transactions"].append(
            {
                "id": transaction.id,
                "datetime": transaction.datetime.isoformat(),
                "category": transaction.category,
                "subcategory": transaction.subcategory,
                "amount": str(transaction.amount),  # Convert Decimal to string
            }
        )

    return JsonResponse(data, safe=False, json_dumps_params={"indent": 2})
