from django.contrib import admin
from .models import Product, Order, OrderItem ,InventoryItem , RentalOrder , RentalItem ,Supplier , Customer

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'available')  # الأعمدة اللي تظهر في القائمة
    list_filter = ('available',)                   # فلتر حسب التوافر
    search_fields = ('name',)                      # البحث حسب الاسم
    list_editable = ('price', 'available')        # تعديل مباشر في القائمة

admin.site.register(Product, ProductAdmin)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_method', 'total_price', 'created_at')  # الأعمدة اللي تظهر في القائمة
    list_filter = ('user', 'payment_method')                                 # فلتر حسب المستخدم وطريقة الدفع
    search_fields = ('user__username',)                                      # البحث حسب اسم المستخدم

admin.site.register(Order, OrderAdmin)


class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'min_limit', 'unit')  # الأعمدة اللي تظهر في القائمة
    list_filter = ('name', 'category')                                 # فلتر حسب المستخدم وطريقة الدفع
    search_fields = ('name',)                                      # البحث حسب اسم المستخدم

admin.site.register(InventoryItem, InventoryItemAdmin)


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')  # الأعمدة اللي تظهر في القائمة
    list_filter = ('order', 'product')                                 # فلتر حسب المستخدم وطريقة الدفع
    search_fields = ('order__id', 'product__name')                                      # البحث حسب اسم المستخدم

admin.site.register(OrderItem, OrderItemAdmin)


@admin.register(RentalOrder)
class RentalOrderAdmin(admin.ModelAdmin):
    list_display = (
        'customer',
        'item',
        'rental_date',
        'return_date',
        'actual_return_date',
        'status',
        'total_price',
    )

    list_filter = (
        'status',
        'rental_date',
        'return_date',
    )

    search_fields = (
        'customer__name',
        'item__name',
    )

@admin.register(RentalItem)
class RentalItemAdmin(admin.ModelAdmin):
    list_display = (
        'item',
        'UID',
        'status',
        'rental_count',
        'profit',
        'is_available',  # property
    )

    list_filter = (
        'status',
        'item',
    )

    search_fields = (
        'UID',
        'item__name',
    )

    # تعريف property للـ availability
    def is_available(self, obj):
        return obj.status is None
    is_available.boolean = True  # يظهر كصح/خطأ
    is_available.short_description = "متاحة للإيجار"

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        "mobil",
      
    )

    search_fields = (
        'name',
    )

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        "mobil",
      
    )

    search_fields = (
        'name',
    )