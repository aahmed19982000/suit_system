from django.contrib import admin
from .models import Product, Order, OrderItem ,InventoryItem

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
