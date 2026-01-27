# 1. الأساسيات والتحويلات
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

# 2. العمليات الحسابية المتقدمة في قاعدة البيانات (ORM)
from django.db import models
from django.db.models import Sum, Avg, Count, Q, F

# 3. الصلاحيات والحماية
from django.contrib.auth.decorators import login_required

# 4. استيراد الموديلات الخاصة بمشروعك 
# (تأكد من تغيير 'your_app_name' إلى اسم المجلد الذي يحتوي على models.py)
from pos.models import (
    Order, 
    OrderItem, 
    Status_order, 
    InventoryItem, 
    Customer, 
    SupplyLog
)


#صفحة لوحة التحكم 
@login_required
def dashboard_view(request):
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # --- 1. إحصائيات المبيعات والطلبات ---
    if request.user.is_staff or request.user.groups.filter(name='Managers').exists():
        daily_orders = Order.objects.filter(created_at__date=today)
        yesterday_orders = Order.objects.filter(created_at__date=yesterday)
    else:
        daily_orders = Order.objects.filter(created_at__date=today, user=request.user)
        yesterday_orders = Order.objects.filter(created_at__date=yesterday, user=request.user)

    total_sales = daily_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    yesterday_sales = yesterday_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # حساب نسبة النمو
    denominator = yesterday_sales if yesterday_sales > 0 else 1
    growth_rate = ((total_sales - yesterday_sales) / denominator) * 100

    # --- 2. إحصائيات المخزون (Inventory) ---
    inventory_stats = InventoryItem.objects.aggregate(
        total_items=models.Count('id'),
        low_stock=models.Count('id', filter=models.Q(quantity__lte=models.F('min_limit'))),
        total_value=models.Sum(models.F('quantity') * models.F('unit_cost'))
    )

    # --- 3. إحصائيات الموردين والديون ---
    supplier_stats = SupplyLog.objects.aggregate(
        total_debts=Sum('remaining_amount'),
        total_paid=Sum('paid_amount')
    )

    # --- 4. إحصائيات العملاء ---
    customer_stats = {
        'total': Customer.objects.count(),
        'active_today': Order.objects.filter(created_at__date=today).values('customer').distinct().count()
    }

    # --- 5. الأصناف الأكثر مبيعاً ---
    best_sellers = OrderItem.objects.filter(order__created_at__date=today) \
        .values('product__name') \
        .annotate(total_qty=Sum('quantity')) \
        .order_by('-total_qty')[:4]

    # --- 6. الطلبات النشطة (Sales + Rental) ---
    # نستخدم استبعاد الحالات المكتملة
    all_statuses = Status_order.objects.all()
    completed_keywords = ["مكتمل", "complete", "done", "تم التسليم"]
    completed_ids = [s.id for s in all_statuses if any(word in str(s).lower() for word in completed_keywords)]
    
    active_orders = Order.objects.filter(created_at__date=today).exclude(status_id__in=completed_ids).order_by('-created_at')[:5]

    context = {
        'total_sales': total_sales,
        'growth_rate': round(growth_rate, 1),
        'abs_growth_rate': abs(round(growth_rate, 1)),
        'inventory_stats': inventory_stats,
        'supplier_stats': supplier_stats,
        'customer_stats': customer_stats,
        'best_sellers': best_sellers,
        'active_orders': active_orders,
        'today_date': today,
        'is_manager': request.user.is_staff,
    }

    return render(request, 'home/dashboard.html', context)
# views.py

#لوحة تحكم الموظف
@login_required
def employee_dashboard(request):
    


    return render(request, 'home/employee_dashboard.html', {
    
    })

# لوحة تحكم المصمم
@login_required
def designer_dashboard(request):
    
   

    return render(request, 'home/designer_dashboard.html', {
    })
