from django.db import models
from categories.models import (
    Category_products, Status_order, Unit_choices, 
    IngredientCategory, Size_choices, Colors_choices, Rental_status_choices
)
from django.conf import settings
from django.db.models import Sum
from django.core.exceptions import ValidationError
import uuid

# --- 1. موديلات المنتجات والعملاء ---

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم المنتج")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")
    available = models.BooleanField(default=True, verbose_name="متاح")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    Category = models.ForeignKey(Category_products, on_delete=models.CASCADE, verbose_name="التصنيف", null=True, blank=True)

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=400, verbose_name="اسم العميل")
    mobil = models.CharField(max_length=15)
    address = models.CharField(max_length=1000, verbose_name="عنوان العميل")
    number_of_orders = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=400, verbose_name="اسم المورد")
    mobil = models.CharField(max_length=15)
    address = models.CharField(max_length=1000, verbose_name="عنوان المورد")
    category = models.CharField(max_length=200, null=True, blank=True, verbose_name="التصنيف")
    number_of_supplies = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def total_debt(self):
        debt = self.supply_history.aggregate(total=Sum('remaining_amount'))['total']
        return debt if debt else 0

    @property
    def total_paid_amount(self):
        paid = self.supply_history.aggregate(total=Sum('paid_amount'))['total']
        return paid if paid else 0

# --- 2. موديلات المخزن والتوريد ---

class InventoryItem(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم الصنف")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='items', verbose_name="الفئة")
    size = models.ForeignKey(Size_choices, on_delete=models.CASCADE, verbose_name="الحجم")
    color = models.ForeignKey(Colors_choices, on_delete=models.CASCADE, verbose_name="اللون")
    quantity = models.PositiveIntegerField(verbose_name="الكمية الحالية")
    min_limit = models.PositiveIntegerField(verbose_name="حد الطلب (الحد الأدنى)")
    unit = models.ForeignKey(Unit_choices, on_delete=models.CASCADE, verbose_name="الوحدة")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر الوحدة")
    supply_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تكلفة التوريد")
    profit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الربح المتوقع")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")
    Supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="المورد")
    is_rental = models.BooleanField(default=False, verbose_name="هل الصنف للإيجار؟")
    rental_code = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False, verbose_name="كود الصنف")
   
    def save(self, *args, **kwargs):
        # حفظ الأساس أولاً
        super().save(*args, **kwargs)

        if self.is_rental:
            # تحديث كود الصنف إذا لم يكن موجوداً
            if not self.rental_code:
                generated_code = f"RENT-{uuid.uuid4().hex[:12].upper()}"
                InventoryItem.objects.filter(pk=self.pk).update(rental_code=generated_code)

            # إدارة قطع الإيجار المادية (منع التكرار)
            existing_count = RentalItem.objects.filter(item=self).count()
            needed = self.quantity - existing_count
            if needed > 0:
                for _ in range(needed):
                    RentalItem.objects.create(item=self)
        else:
            # تنظيف البيانات إذا تم إيقاف خيار الإيجار
            if self.rental_code:
                InventoryItem.objects.filter(pk=self.pk).update(rental_code=None)
                RentalItem.objects.filter(item=self).delete()

    @property
    def total_value(self):
        return self.quantity * self.unit_cost

    @property
    def is_low(self):
        return self.quantity <= self.min_limit

    def __str__(self):
        return self.name

class SupplyLog(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supply_history', verbose_name="المورد")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, null=True, blank=True, verbose_name="الصنف المورد")
    quantity_added = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="الكمية المضافة")
    cost_at_time = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="سعر الوحدة عند الشراء")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="إجمالي قيمة الطلبية")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="المبلغ المدفوع")
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="المبلغ المتبقي (دين)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التوريد")

    def save(self, *args, **kwargs):
        from decimal import Decimal
        quantity = Decimal(str(self.quantity_added or 0))
        cost = Decimal(str(self.cost_at_time or 0))
        paid = Decimal(str(self.paid_amount or 0))

        if self.item:
            self.total_amount = quantity * cost
            self.remaining_amount = self.total_amount - paid
        else:
            self.total_amount = Decimal('0.00')
            self.remaining_amount = - paid
        super().save(*args, **kwargs)

# --- 3. موديلات الطلبات والإيجار ---

class Order(models.Model):
    PAYMENT_CHOICES = (('cash', 'Cash'), ('visa', 'Visa'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, verbose_name="العميل")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey(Status_order, on_delete=models.CASCADE, verbose_name="حالة الطلب", null=True, blank=True, default=1)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class RentalItem(models.Model):
    UID = models.CharField(max_length=50, unique=True, verbose_name="كود البدلة", editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, verbose_name="البدلة", limit_choices_to={'is_rental': True})
    rental_count = models.PositiveIntegerField(default=0, verbose_name="عدد مرات الإيجار")
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="الربح من الإيجار")
    status = models.ForeignKey(Rental_status_choices, on_delete=models.CASCADE, verbose_name="حالة البدلة", null=True, blank=True, default=1)

    def save(self, *args, **kwargs):
        if not self.UID:
            self.UID = f"RENT-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} - {self.UID}"



class RentalOrder(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        verbose_name="العميل"
    )

    item = models.ForeignKey(
        RentalItem,
        on_delete=models.CASCADE,
        verbose_name="البدلة"
    )

    rental_date = models.DateField(
        verbose_name="تاريخ الحجز / الخروج"
    )

    return_date = models.DateField(
        verbose_name="تاريخ العودة المتوقع"
    )

    size = models.ForeignKey(
        Size_choices,
        on_delete=models.CASCADE,
        verbose_name="المقاس"
    )

    # ✅ اسم نظيف (underscore حقيقي)
    pants_size = models.CharField(
        max_length=50,
        verbose_name="مقاس البنطلون"
    )

    color = models.ForeignKey(
        Colors_choices,
        on_delete=models.CASCADE,
        verbose_name="اللون"
    )

    actual_return_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ العودة الفعلي"
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="قيمة الإيجار"
    )

    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="مبلغ التأمين"
    )

    # ❌ بدون default — الحالة تتحدد من الـ business logic
    status = models.ForeignKey(
        Rental_status_choices,
        on_delete=models.CASCADE,
        verbose_name="حالة البدلة",
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات (مقاسات، تعديلات)"
    )
    late_damage_penalty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="غرامة التأخير أو التلف",
        null=True,
        blank=True
    )

    # =========================
    # Validation Logic
    # =========================
    def clean(self):
        """
        التحقق من صحة الحجز قبل الحفظ
        """

        if not self.item:
            raise ValidationError("يجب اختيار بدلة")

        inventory_item = self.item.item

        # 1️⃣ التأكد إن الصنف قابل للإيجار
        if not inventory_item.is_rental:
            raise ValidationError("هذا الصنف غير متاح للإيجار")

        # 2️⃣ التحقق من الكمية (عند الإنشاء فقط)
        if self.pk is None and inventory_item.quantity <= 0:
            raise ValidationError("لا توجد قطع متاحة للإيجار حالياً")

        # 3️⃣ منع الحجز المكرر لنفس البدلة
        try:
            reserved_status = Rental_status_choices.objects.get(status="محجوز")
        except Rental_status_choices.DoesNotExist:
            return  # لو الحالة مش موجودة، منوقفش النظام

        is_reserved = RentalOrder.objects.filter(
            item=self.item,
            status=reserved_status
        ).exclude(pk=self.pk).exists()

        if is_reserved:
            raise ValidationError(
                "هذه البدلة محجوزة بالفعل ولا يمكن حجزها مرة أخرى"
            )

    # =========================
    # String Representation
    # =========================
    def __str__(self):
        return f"تأجير {self.item.item.name} - {self.customer.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, verbose_name="الصنف")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر البيع")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الكمية")
    rental_order = models.ForeignKey(RentalOrder, on_delete=models.CASCADE, null=True, blank=True, verbose_name="طلب إيجار") 

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def get_total_item_price(self):
        return self.price * self.quantity