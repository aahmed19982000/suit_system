from django.db import models
from categories.models import Category_products ,Status_order , Unit_choices ,IngredientCategory , Size_choices , Colors_choices
from django.conf import settings
from django.db.models import Sum

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
    
class Supplier(models.Model):
    name = models.CharField(max_length=400, verbose_name="اسم المورد")
    mobil = models.CharField(max_length=15)
    address = models.CharField(max_length=1000, verbose_name="عنوان المورد")
    category = models.CharField(max_length=200, null=True, blank=True, verbose_name="التصنيف") # أضفنا هذا الحقل
    number_of_supplies = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def total_debt(self):
        """حساب إجمالي المديونية الحالية للمورد"""
        debt = self.supply_history.aggregate(total=Sum('remaining_amount'))['total']
        return debt if debt else 0

    @property
    def total_paid_amount(self):
        """حساب إجمالي ما تم دفعه للمورد منذ البداية"""
        paid = self.supply_history.aggregate(total=Sum('paid_amount'))['total']
        return paid if paid else 0


class InventoryItem(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم الصنف")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='items', verbose_name="الفئة")
    size = models.ForeignKey(Size_choices, on_delete=models.CASCADE, verbose_name="الحجم", null=True, blank=True)
    color = models.ForeignKey(Colors_choices, on_delete=models.CASCADE, verbose_name="اللون", null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الكمية الحالية")
    min_limit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="حد الطلب (الحد الأدنى)")
    unit = models.ForeignKey(Unit_choices, on_delete=models.CASCADE, verbose_name="الوحدة")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر الوحدة")
    supply_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تكلفة التوريد", default=0)
    profit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الربح المتوقع", default=0)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")
    Supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="المورد", null=True, blank=True)

    @property
    def total_value(self):
        return self.quantity * self.unit_cost

    @property
    def is_low(self):
        return self.quantity <= self.min_limit

    def __str__(self):
        return self.name


class SupplyLog(models.Model):
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE, 
        related_name='supply_history', 
        verbose_name="المورد"
    )
    # التعديل: null=True و blank=True مهم جداً للسداد المالي
    item = models.ForeignKey(
        InventoryItem, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="الصنف المورد"
    )
    quantity_added = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="الكمية المضافة")
    cost_at_time = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="سعر الوحدة عند الشراء")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="إجمالي قيمة الطلبية")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="المبلغ المدفوع")
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="المبلغ المتبقي (دين)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التوريد")

    def save(self, *args, **kwargs):
        # إذا كان هناك صنف، نحسب الإجمالي بناءً على الكمية والسعر
        if self.item:
            self.total_amount = self.quantity_added * self.cost_at_time
            self.remaining_amount = self.total_amount - self.paid_amount
        else:
            # في حالة السداد النقدي فقط
            self.total_amount = 0
            # المدفوع ينقص من المديونية الإجمالية
            self.remaining_amount = - self.paid_amount
            
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.item.name if self.item else "سداد مالي"
        return f"{name} - {self.supplier.name} ({self.created_at.date()})"