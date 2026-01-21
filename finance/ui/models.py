## models.py
from django.db import models


class Category(models.Model):
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100)
    total_sum = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        # Composite primary key using unique_together (Django doesn't support composite PK directly)
        constraints = [
            models.UniqueConstraint(
                fields=["category", "subcategory"], name="unique_category_subcategory"
            )
        ]
        # Alternative: You can also use unique_together
        # unique_together = [['category', 'subcategory']]

    def __str__(self):
        return f"{self.category} - {self.subcategory}"


class Transaction(models.Model):
    datetime = models.DateTimeField()
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Optional foreign key relationship to Category
    # category_ref = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.datetime} - {self.category} - {self.amount}"

    def save(self, *args, **kwargs):
        # You could add logic here to update the sum in Category table
        # when a transaction is saved
        super().save(*args, **kwargs)  # Create your models here.
