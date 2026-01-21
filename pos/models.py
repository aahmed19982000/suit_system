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
        # التأكد من تحويل كل القيم إلى Decimal لتجنب أخطاء النوع
        from decimal import Decimal
        quantity = Decimal(str(self.quantity_added or 0))
        cost = Decimal(str(self.cost_at_time or 0))
        paid = Decimal(str(self.paid_amount or 0))

        if self.item:
            # عملية توريد صنف: الإجمالي = الكمية * السعر
            self.total_amount = quantity * cost
            self.remaining_amount = self.total_amount - paid
        else:
            # عملية سداد نقدي فقط: لا يوجد إجمالي صنف
            self.total_amount = Decimal('0.00')
            self.quantity_added = Decimal('0.00')
            self.cost_at_time = Decimal('0.00')
            # المتبقي هنا يكون بالسالب لأنه يخصم من مديونية المورد الكلية
            self.remaining_amount = - paid
            
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.item.name if self.item else "سداد مالي"
        return f"{name} - {self.supplier.name} ({self.created_at.date()})"
    

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    # التعديل هنا: نربطه بالمخزن بدلاً من Product
    product = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, verbose_name="الصنف")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر البيع")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الكمية")
    rental_order = models.ForeignKey(
        'RentalOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="طلب إيجار"
    ) 

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property # استخدم property أفضل من دالة عادية لسهولة الاستدعاء في القوالب
    def get_total_item_price(self):
        return self.price * self.quantity
    


# في ملف models.py

class RentalOrder(models.Model):
    STATUS_CHOICES = (
        ('booked', 'محجوز'),
        ('picked_up', 'تم الاستلام'),
        ('returned', 'تم الترجيع'),
        ('late', 'متأخر'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="العميل")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, verbose_name="البدلة")
    rental_date = models.DateField(verbose_name="تاريخ الحجز/الخروج")
    return_date = models.DateField(verbose_name="تاريخ العودة المتوقع")
    actual_return_date = models.DateField(null=True, blank=True, verbose_name="تاريخ العودة الفعلي")
    
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قيمة الإيجار")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ التأمين")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات (مقاسات، تعديلات)")
    total_rentals = models.PositiveIntegerField(default=0, verbose_name="إجمالي مرات الإيجار")
    total_profit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="إجمالي الربح من الإيجار", default=0)

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="رقم الفاتورة"
    )

    def __str__(self):
        return f"تأجير {self.item.name} - {self.customer.name}"