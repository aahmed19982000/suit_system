from django.shortcuts import render
from .models import Product , Customer
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProductForm
from django.contrib import messages
from categories.models import Category_products , Unit_choices
from django.contrib.auth import get_user_model
from accounts.decorators import role_required
from django.views.decorators.http import require_POST
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem , Status_order , InventoryItem, IngredientCategory
from django.db.models import Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator

# Create your views here.



def search_customer(request):
    phone = request.GET.get('phone')
    # البحث عن العميل باستخدام رقم الهاتف (حقل mobil في الموديل الخاص بك)
    customer = Customer.objects.filter(mobil=phone).first()
    
    if customer:
        return JsonResponse({
            'found': True,
            'id': customer.id,
            'name': customer.name,
            'address': customer.address
        })
    else:
        return JsonResponse({'found': False})


@csrf_exempt
@login_required
def cash_checkout(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        cart = data.get('cart', [])
        total = data.get('total')
        order_type = data.get('order_type')
        cust_data = data.get('customer_data')

        from .models import Customer, Order, OrderItem, Product

        customer_obj = None
        # منطق الدليفري والتعامل مع موديل Customer
        if order_type == 'delivery' and cust_data:
            customer_obj, created = Customer.objects.get_or_create(
                mobil=cust_data['phone'],
                defaults={'name': cust_data['name'], 'address': cust_data['address']}
            )
            if not created: # تحديث البيانات إذا كان العميل موجوداً مسبقاً
                customer_obj.name = cust_data['name']
                customer_obj.address = cust_data['address']
                customer_obj.save()
            
            # تحديث عدد طلبات العميل
            customer_obj.number_of_orders += 1
            customer_obj.save()

        # إنشاء الطلب
        order = Order.objects.create(
            user=request.user,
            customer=customer_obj, # ربط العميل بالطلب
            payment_method='cash',
            total_price=total
        )

        # إضافة الأصناف
        for item in cart:
            product = Product.objects.get(id=item['id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                price=item['price'],
                quantity=item['qty']
            )

        return JsonResponse({
            'status': 'success',
            'order_id': order.id
        })



@login_required
def pos_page(request):
    # جلب جميع المنتجات المتاحة
    products = Product.objects.filter(available=True)
    # جلب جميع التصنيفات لعرضها في الفلاتر
    categories = Category_products.objects.all()

    #تنفيذ الطلبات في السلة 

    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'pos/pos_page.html', context)


@role_required('manager')
def menu_management(request, product_id=None):
    """
    إدارة المنيو: إضافة، تعديل، حذف
    """
    if product_id:
        product = get_object_or_404(Product, id=product_id)
    else:
        product = None

    # عملية الإضافة أو التعديل
    if request.method == 'POST':
        if 'delete' in request.POST and product:
            product.delete()
            messages.success(request, 'تم حذف المنتج بنجاح!')
            return redirect('menu_management')

        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            if product:
                messages.success(request, 'تم تعديل المنتج بنجاح!')
            else:
                messages.success(request, 'تم إضافة المنتج بنجاح!')
            return redirect('menu_management')
        else:
            messages.error(request, 'هناك خطأ في البيانات، يرجى التحقق.')
    else:
        form = ProductForm(instance=product)

    products = Product.objects.all()
    return render(request, 'pos/menu_management.html', {
        'form': form,
        'products': products,
        'editing_product': product
    })




def inventory_management(request):
    # جلب جميع الأصناف
    items = InventoryItem.objects.all().order_by('name')
    categories = IngredientCategory.objects.all()
    
    # جلب الوحدات لتكون متوافقة مع حقل ForeignKey في الموديل
    units = Unit_choices.objects.all()

    # 1. إحصائية إجمالي الأصناف
    total_items_count = items.count()

    # 2. إحصائية الأصناف المنخفضة
    low_stock_items = [item for item in items if item.is_low]
    low_stock_count = len(low_stock_items)

    # 3. إحصائية قيمة المخزون الإجمالية
    inventory_value = sum(item.total_value for item in items)

    # فلترة حسب الفئة إذا تم اختيارها
    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        items = items.filter(category_id=category_filter)

    context = {
        'items': items,
        'categories': categories,
        'units': units,  # أضفنا الوحدات هنا ليتم عرضها في modal الإضافة
        'total_items_count': total_items_count,
        'low_stock_count': low_stock_count,
        'low_stock_items': low_stock_items[:3],  
        'inventory_value': inventory_value,
        'selected_category': category_filter,
    }
    return render(request, 'pos/inventory_management.html', context)

@require_POST
@role_required('manager')
def add_inventory_item(request):
    try:
        # استلام البيانات
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        unit_id = request.POST.get('unit') # استلام الـ ID الخاص بالوحدة
        quantity = request.POST.get('quantity')
        min_limit = request.POST.get('min_limit')
        unit_cost = request.POST.get('unit_cost')

        # جلب الكائنات المرتبطة
        category = get_object_or_404(IngredientCategory, id=category_id)
        unit_obj = get_object_or_404(Unit_choices, id=unit_id)
        
        # إنشاء الصنف
        InventoryItem.objects.create(
            name=name,
            category=category,
            unit=unit_obj, # حفظ الكائن المربوط
            quantity=quantity,
            min_limit=min_limit,
            unit_cost=unit_cost
        )

        return JsonResponse({'status': 'success', 'message': 'تم إضافة الصنف بنجاح'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def update_inventory_quantity(request):
    item_id = request.POST.get('item_id')
    amount_raw = request.POST.get('amount', '0').strip()
    action = request.POST.get('action')

    try:
        # تنظيف النص من أي رموز غير رقمية قد تأتي من المتصفح
        amount_clean = "".join(filter(lambda x: x in "0123456789.", amount_raw))
        
        # محاولة التحويل
        amount = Decimal(amount_clean)
        
        if amount <= 0:
            return JsonResponse({'status': 'error', 'message': 'يجب إدخال رقم أكبر من الصفر'}, status=400)

        item = get_object_or_404(InventoryItem, id=item_id)

        if action == 'add':
            item.quantity += amount
            item.save()
            return JsonResponse({'status': 'success', 'message': f'تم إضافة {amount} بنجاح'})
        
        elif action == 'subtract':
            if item.quantity < amount:
                return JsonResponse({'status': 'error', 'message': 'المخزون الحالي لا يكفي'}, status=400)
            item.quantity -= amount
            item.save()
            return JsonResponse({'status': 'success', 'message': f'تم خصم {amount} بنجاح'})

    except (InvalidOperation, ValueError):
        return JsonResponse({'status': 'error', 'message': f'القيمة ({amount_raw}) ليست رقماً صالحاً'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'خطأ غير متوقع في النظام'}, status=500)

User = get_user_model()

def sales_reports(request):
    user = request.user
    now = timezone.now()
    
    # 1. جلب بارامترات الفلترة من الرابط (GET)
    filter_type = request.GET.get('range', 'today')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    staff_id = request.GET.get('staff_id', 'all')
    selected_status = request.GET.get('status_id', 'all')
    
    # 2. بناء استعلام التاريخ (Date Filter Query)
    query_date = Q()
    if filter_type == 'today':
        query_date &= Q(created_at__date=now.date())
    elif filter_type == 'week':
        query_date &= Q(created_at__gte=now - timedelta(days=7))
    elif filter_type == 'month':
        query_date &= Q(created_at__month=now.month, created_at__year=now.year)
    elif filter_type == 'custom' and start_date and end_date:
        query_date &= Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
    elif selected_status and selected_status != 'all':
        query_date &= Q(status_id=selected_status)

    # 3. إدارة الصلاحيات وفلتر الموظفين
    staff_members = None
    selected_staff_name = None
    
    # التحقق مما إذا كان المستخدم مديراً (Manager)
    if hasattr(user, 'role') and user.role == 'manager':
        is_manager = True
        # جلب جميع المستخدمين ليعرضهم المدير في القائمة المنسدلة
        staff_members = User.objects.all() 
        
        # إذا اختار المدير موظفاً معيناً من القائمة
        if staff_id and staff_id != 'all':
            query_date &= Q(user_id=staff_id)
            staff_obj = User.objects.filter(id=staff_id).first()
            if staff_obj:
                selected_staff_name = staff_obj.get_full_name() or staff_obj.username
    else:
        # إذا كان موظفاً عادياً، تظهر بياناته هو فقط ولا يمكنه تغيير الفلتر
        is_manager = False
        query_date &= Q(user=user)

    # 4. جلب الطلبات بناءً على الفلترة النهائية
    report_orders = Order.objects.filter(query_date)
    all_statuses = Status_order.objects.all()
    
    # 5. حساب الإحصائيات المالية
    stats = {
        'total_sales': report_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'orders_count': report_orders.count(),
        'avg_order': report_orders.aggregate(Avg('total_price'))['total_price__avg'] or 0,
    }

    # 6. الأصناف الأكثر مبيعاً (Top 5)
    best_sellers = OrderItem.objects.filter(order__in=report_orders) \
        .values('product__name') \
        .annotate(total_qty=Sum('quantity')) \
        .order_by('-total_qty')[:5]

    # 7. تجهيز السياق للقالب (Template Context)
    context = {
        'stats': stats,
        'best_sellers': best_sellers,
        'recent_orders': report_orders.prefetch_related('items__product').order_by('-created_at')[:10],
        'is_manager': is_manager,
        'staff_members': staff_members,
        'selected_staff': staff_id,
        'selected_staff_name': selected_staff_name,
        'filter_type': filter_type,
        'now': now,
        'all_statuses': all_statuses,
        'selected_status': selected_status,
    }
    
    return render(request, 'pos/sales_reports.html', context)


def customer_management(request):
    # 1. جلب بارامترات البحث والفلترة من الرابط
    search_query = request.GET.get('search', '')
    filter_tab = request.GET.get('tab', 'all')
    page_number = request.GET.get('page', 1)

    # 2. الاستعلام الأساسي عن العملاء
    customers_list = Customer.objects.all().order_by('-id')

    # 3. تطبيق البحث (بالاسم أو الهاتف)
    if search_query:
        customers_list = customers_list.filter(
            Q(name__icontains=search_query) | 
            Q(mobil__icontains=search_query)
        )

    # 4. تطبيق الفلترة (Tabs)
    if filter_tab == 'frequent': # الأكثر طلباً
        customers_list = customers_list.order_by('-number_of_orders')
    elif filter_tab == 'new': # عملاء جدد (آخر 30 يوم)
        last_month = timezone.now() - timedelta(days=30)
        # ملاحظة: إذا لم يكن لديك حقل تاريخ إضافة العميل، سنفترض ترتيب ID
        customers_list = customers_list.order_by('-id')[:50] 

    # 5. حساب الإحصائيات (Stats)
    now = timezone.now()
    total_customers = Customer.objects.count()
    
    # عملاء جدد هذا الشهر (افتراضاً بناءً على عدد الطلبات أو الترقيم)
    new_customers_this_month = Customer.objects.filter(number_of_orders__lte=1).count()
    
    # العملاء النشطين (الذين لديهم أكثر من 5 طلبات مثلاً)
    active_customers = Customer.objects.filter(number_of_orders__gt=5).count()
    
    # متوسط الطلبات (كبديل لنقاط الولاء إذا لم تكن موجودة)
    avg_orders = Customer.objects.aggregate(Avg('number_of_orders'))['number_of_orders__avg'] or 0

    # 6. التقسيم لصفحات (Pagination) - 10 عملاء لكل صفحة
    paginator = Paginator(customers_list, 10)
    page_obj = paginator.get_page(page_number)

    context = {
        'customers': page_obj,
        'total_customers': total_customers,
        'new_customers_count': new_customers_this_month,
        'active_customers': active_customers,
        'avg_orders': round(avg_orders, 1),
        'search_query': search_query,
        'current_tab': filter_tab,
    }

    return render(request, 'pos/customer_management.html', context)


def employees_management(request):
    return render(request, 'pos/employees_management.html')






User = get_user_model()

def orders(request):
    user = request.user
    staff_members = None
    
    if hasattr(user, 'role') and user.role == 'manager':
        # المدير يرى كل الطلبات وكل الموظفين
        all_orders = Order.objects.all().prefetch_related('items__product').order_by('-created_at')
        total_sales = all_orders.aggregate(Sum('total_price'))['total_price__sum']
        staff_members = User.objects.all() # جلب الموظفين للفلتر
    else:
        # الموظف يرى طلباته فقط
        all_orders = Order.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')
        total_sales = all_orders.aggregate(Sum('total_price'))['total_price__sum']

    context = {
        'orders': all_orders,
        'total_sales': total_sales or 0,
        'staff_members': staff_members, # إرسال الموظفين للقالب
    }
    return render(request, 'pos/orders.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # التحقق من الصلاحيات: الموظف يرى طلباته فقط، المدير يرى الكل
    if request.user.role != 'manager' and order.user != request.user:
        messages.error(request, "ليس لديك صلاحية للوصول لهذا الطلب")
        return redirect('orders')
    
    return render(request, 'pos/order_detail.html', {'order': order})




@login_required
def process_order_action(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    action = request.POST.get('action')
    # تأكد من أن حقل role موجود في موديل المستخدم لديك
    user_role = getattr(request.user, 'role', 'staff') 

    if action == 'return':
        # استخدام حقل status بدلاً من name بناءً على بنية الموديل لديك
        try:
            # سنحاول جلب الحالة التي تحتوي على كلمة "مرتجع"
            returned_status = Status_order.objects.filter(status__icontains="مرتجع").first()
            
            if returned_status:
                order.status = returned_status
                order.save()
                messages.success(request, f"تم إرجاع الطلب #{order.id} بنجاح")
            else:
                messages.error(request, "لم يتم العثور على حالة باسم 'مرتجع' في قاعدة البيانات")
        except Exception as e:
            messages.error(request, f"خطأ فني: {str(e)}")

    elif action == 'delete':
        if user_role == 'manager':
            order.delete()
            messages.success(request, "تم حذف الطلب نهائياً")
            return redirect('orders') # تأكد من وجود رابط بهذا الاسم في urls.py
        else:
            messages.error(request, "عذراً، صلاحية الحذف للمدير فقط")

    elif action == 'edit_payment':
        if user_role == 'manager':
            new_method = request.POST.get('payment_method')
            if new_method in ['cash', 'visa']:
                order.payment_method = new_method
                order.save()
                messages.success(request, "تم تحديث طريقة الدفع بنجاح")
            else:
                messages.error(request, "طريقة دفع غير صالحة")
        else:
            messages.error(request, "عذراً، صلاحية التعديل للمدير فقط")

    return redirect('order_detail', order_id=order.id)