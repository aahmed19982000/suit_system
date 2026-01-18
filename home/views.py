from django.shortcuts import render 
from django.contrib.auth.decorators import login_required 
from accounts.decorators import role_required
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from pos.models import Order, OrderItem, Product  # تأكد من مسميات الموديلات لديك
from datetime import timedelta
from categories.models import Status_order


#صفحة لوحة التحكم 
@login_required
def dashboard_view(request):
    today = timezone.now().date()
    
    # 1. فلترة الطلبات حسب الرتبة
    if request.user.is_staff or request.user.groups.filter(name='Managers').exists():
        daily_orders = Order.objects.filter(created_at__date=today)
    else:
        daily_orders = Order.objects.filter(created_at__date=today, user=request.user)
    
    is_manager = request.user.is_staff or request.user.groups.filter(name='Managers').exists()

    # 2. الإحصائيات المالية
    total_sales = daily_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_orders_count = daily_orders.count()
    
    # --- الحل الجديد والأكثر أماناً ---
    # بدلاً من البحث عن اسم الحقل، نجلب كل الحالات ونبحث فيها برمجياً
    all_statuses = Status_order.objects.all()
    
    # تحديد ID حالة التحضير (نبحث عن أي حالة تحتوي كلماتها على "تحضير" أو "prep")
    preparing_status_ids = [s.id for s in all_statuses if "تحضير" in str(s) or "prep" in str(s).lower()]
    preparing_orders_count = daily_orders.filter(status_id__in=preparing_status_ids).count()

    # تحديد ID الحالات المكتملة لاستبعادها من "الطلبات النشطة"
    completed_status_ids = [s.id for s in all_statuses if "مكتمل" in str(s) or "complete" in str(s).lower() or "done" in str(s).lower()]
    active_orders = daily_orders.exclude(status_id__in=completed_status_ids).order_by('-created_at')
    # ----------------------------

    average_order_value = daily_orders.aggregate(Avg('total_price'))['total_price__avg'] or 0

    # 4. حساب نسبة النمو
    yesterday = today - timedelta(days=1)
    yesterday_sales = Order.objects.filter(created_at__date=yesterday).aggregate(Sum('total_price'))['total_price__sum'] or 0
    denominator = yesterday_sales if yesterday_sales > 0 else 1
    growth_rate = ((total_sales - yesterday_sales) / denominator) * 100

    # 5. الأصناف الأكثر مبيعاً
    best_sellers = OrderItem.objects.filter(order__created_at__date=today) \
        .values('product__name') \
        .annotate(total_qty=Sum('quantity')) \
        .order_by('-total_qty')[:4]

    context = {
        'total_sales': total_sales,
        'total_orders_count': total_orders_count,
        'preparing_orders_count': preparing_orders_count,
        'average_order_value': average_order_value,
        'growth_rate': round(growth_rate, 1),
        'abs_growth_rate': abs(round(growth_rate, 1)),
        'best_sellers': best_sellers,
        'active_orders': active_orders,
        'is_manager': is_manager,
        'today_date': today,
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
