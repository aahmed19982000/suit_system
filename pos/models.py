from django.db import models
from categories.models import Category_products ,Status_order , Unit_choices ,IngredientCategory
from django.conf import settings

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم المنتج")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")
    available = models.BooleanField(default=True, verbose_name="متاح")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    Category = models.ForeignKey(Category_products,on_delete=models.CASCADE,verbose_name="التصنيف",null=True,blank=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    PAYMENT_CHOICES = (
        ('cash', 'Cash'),
        ('visa', 'Visa'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="العميل"
    )

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    status = models.ForeignKey(
        Status_order,
        on_delete=models.CASCADE,
        verbose_name="حالة الطلب",
        null=True,
        blank=True,
        default=1
    )


    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',  # 🔥 المهم هنا
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def total_price(self):
        return self.price * self.quantity
    


class Customer(models.Model):
    name= models.CharField(max_length=400, verbose_name="اسم العميل")
    mobil=models.CharField(max_length=15)
    address =models.CharField(max_length=1000, verbose_name="عنوان العميل")
    number_of_orders = models.PositiveIntegerField(default=0)


    def __str__(self):
        return self.name
    


class InventoryItem(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم الصنف")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='items', verbose_name="الفئة")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الكمية الحالية")
    min_limit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="حد الطلب (الحد الأدنى)")
    unit =  models.ForeignKey(Unit_choices, on_delete=models.CASCADE, verbose_name="الوحدة")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر الوحدة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    @property
    def total_value(self):
        return self.quantity * self.unit_cost

    @property
    def is_low(self):
        return self.quantity <= self.min_limit

    def __str__(self):
        return self.name