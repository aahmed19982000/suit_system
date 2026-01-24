from django.urls import path
from . import views

urlpatterns = [
    # --- 1. المسارات الرئيسية الثابتة ---
    path('', views.pos_page, name='pos_page'),
    path('menu/', views.menu_management, name='menu_management'),
    path('inventory/', views.inventory_management, name='inventory_management'),
    path('sales-reports/', views.sales_reports, name='sales_reports'),
    path('orders/', views.orders, name='orders'),
    path('customer-management/', views.customer_management, name='customer_management'),
    path('employees-management/', views.employees_management, name='employees_management'),
    

    # --- 2. إدارة الموردين (دقيقة جداً - يجب أن تسبق الـ IDs العامة) ---
    path('supplies-management/', views.supplies_management, name='supplies_management'),
    # هذا الرابط الذي يطلبه الـ Fetch
    path('supplies-management/get-logs/<int:supplier_id>/', views.get_supplier_logs, name='get_supplier_logs'),
    path('supplies-management/pay-debt/', views.pay_supplier_debt, name='pay_supplier_debt'),
    path('supplies-management/log/delete/<int:log_id>/', views.delete_supply_log, name='delete_supply_log'),
    path('supplies-management/log/edit/<int:log_id>/', views.edit_supply_log, name='edit_supply_log'),
    path('supplies-management/delete/<int:pk>/', views.delete_supplier, name='delete_supplier'),
    path('check-supplier/', views.check_supplier_by_phone, name='check_supplier_by_phone'),
    
    

    # --- 3. مسارات العمليات (POST) ---
    path('inventory/add/', views.add_inventory_item, name='add_inventory_item'),
    path('inventory/update/', views.update_inventory_quantity, name='update_inventory'),
    path('checkout/cash/', views.cash_checkout, name='cash_checkout'),
    path('rental/', views.pos_rental_page, name='pos_rental_page'),
    path('rental/checkout/', views.rental_checkout, name='rental_checkout'),
    path('create_customer_ajax/', views.create_customer_ajax, name='create_customer_ajax'),
    path('search-customer/', views.search_customer, name='search_customer'),
    path('search-uid/', views.search_UID, name='search_UID'),
    path('rental_items/', views.all_rental_items, name='all_rental_items'),  
    path('rental_items/update_status/<int:pk>/', views.update_rental_status, name='update_rental_status'),
    
    

    # --- 4. المسارات التي تبدأ بمتغير <int> (اجعلها في نهاية الملف دائماً) ---
    # إذا وضعت هذه في الأعلى، سيعتقد Django أن "supplies-management" هي order_id ويعطي 404
    path('menu/<int:product_id>/', views.menu_management, name='menu_management'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/action/', views.process_order_action, name='process_order_action'),
    path('inventory/edit/', views.edit_inventory_item, name='edit_inventory_item'),
    path('inventory/delete/', views.delete_inventory_item, name='delete_inventory_item'),
    

]