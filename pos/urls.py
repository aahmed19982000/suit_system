from django.urls import path
from . import views


urlpatterns = [
    path('', views.pos_page, name='pos_page'),
    path('menu/', views.menu_management, name='menu_management'),
    path('inventory/', views.inventory_management, name='inventory_management'),
    path('sales-reports/', views.sales_reports, name='sales_reports'),
    path('customer-management/', views.customer_management, name='customer_management'),
    path('employees-management/', views.employees_management, name='employees_management'),
    path('menu/<int:product_id>/', views.menu_management, name='menu_management'),
    path('checkout/cash/', views.cash_checkout, name='cash_checkout'),
    path('orders/', views.orders, name='orders'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/action/', views.process_order_action, name='process_order_action'),
    path('inventory/add/', views.add_inventory_item, name='add_inventory_item'),
    
    # الرابط الجديد المفقود لتحديث الكميات (إضافة/خصم)
    path('inventory/update/', views.update_inventory_quantity, name='update_inventory'),
    path('pos/search-customer/', views.search_customer, name='search_customer'),
    path('check-supplier/', views.check_supplier_by_phone, name='check_supplier_by_phone'),
    path('supplies-management/', views.supplies_management, name='supplies_management'),
    path('delete-supplier/<int:pk>/', views.delete_supplier, name='delete_supplier'),
    path('suppliers/get-logs/<int:supplier_id>/', views.get_supplier_logs, name='get_supplier_logs'),
    path('suppliers/pay-debt/', views.pay_supplier_debt, name='pay_supplier_debt'),
    path('suppliers/get-logs/<int:supplier_id>/', views.get_supplier_logs, name='get_supplier_logs'),
]
