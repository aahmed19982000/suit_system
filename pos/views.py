from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.db.models import Sum, Avg, Q, F
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator

import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

# استيراد الموديلات
from .models import (
    Product, Customer, Supplier, SupplyLog, Order, 
    OrderItem, Status_order, InventoryItem, IngredientCategory
)
from .forms import ProductForm
from categories.models import Category_products, Unit_choices, Size_choices, Colors_choices
from accounts.decorators import role_required

User = get_user_model()

# ================= CUSTOMER VIEWS =================

def search_customer(request):
    phone = request.GET.get('phone')
    customer = Customer.objects.filter(mobil=phone).first()
    if customer:
        return JsonResponse({
            'found': True,
            'id': customer.id,
            'name': customer.name,
            'address': customer.address
        })
    return JsonResponse({'found': False})

def customer_management(request):
    search_query = request.GET.get('search', '')
    filter_tab = request.GET.get('tab', 'all')
    page_number = request.GET.get('page', 1)

    customers_list = Customer.objects.all().order_by('-id')

    if search_query:
        customers_list = customers_list.filter(
            Q(name__icontains=search_query) | Q(mobil__icontains=search_query)
        )

    if filter_tab == 'frequent':
        customers_list = customers_list.order_by('-number_of_orders')
    elif filter_tab == 'new':
        customers_list = customers_list.order_by('-id')[:50] 

    total_customers = Customer.objects.count()
    new_customers_this_month = Customer.objects.filter(number_of_orders__lte=1).count()
    active_customers = Customer.objects.filter(number_of_orders__gt=5).count()
    avg_orders = Customer.objects.aggregate(Avg('number_of_orders'))['number_of_orders__avg'] or 0

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

# ================= POS & ORDER VIEWS =================

@login_required
def pos_page(request):
    products = Product.objects.filter(available=True)
    categories = Category_products.objects.all()
    return render(request, 'pos/pos_page.html', {'products': products, 'categories': categories})

@csrf_exempt
@login_required
def cash_checkout(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        cart = data.get('cart', [])
        total = data.get('total')
        order_type = data.get('order_type')
        cust_data = data.get('customer_data')

        customer_obj = None
        if order_type == 'delivery' and cust_data:
            customer_obj, created = Customer.objects.get_or_create(
                mobil=cust_data['phone'],
                defaults={'name': cust_data['name'], 'address': cust_data['address']}
            )
            if not created:
                customer_obj.name = cust_data['name']
                customer_obj.address = cust_data['address']
            customer_obj.number_of_orders += 1
            customer_obj.save()

        order = Order.objects.create(
            user=request.user,
            customer=customer_obj,
            payment_method='cash',
            total_price=total
        )

        for item in cart:
            product = Product.objects.get(id=item['id'])
            OrderItem.objects.create(
                order=order, product=product,
                price=item['price'], quantity=item['qty']
            )

        return JsonResponse({'status': 'success', 'order_id': order.id})

def orders(request):
    user = request.user
    staff_members = None
    if hasattr(user, 'role') and user.role == 'manager':
        all_orders = Order.objects.all().prefetch_related('items__product').order_by('-created_at')
        staff_members = User.objects.all()
    else:
        all_orders = Order.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')
    
    total_sales = all_orders.aggregate(Sum('total_price'))['total_price__sum']
    return render(request, 'pos/orders.html', {'orders': all_orders, 'total_sales': total_sales or 0, 'staff_members': staff_members})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if getattr(request.user, 'role', 'staff') != 'manager' and order.user != request.user:
        messages.error(request, "ليس لديك صلاحية للوصول لهذا الطلب")
        return redirect('orders')
    return render(request, 'pos/order_detail.html', {'order': order})

@login_required
@require_POST
def process_order_action(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    action = request.POST.get('action')
    user_role = getattr(request.user, 'role', 'staff') 

    if action == 'return':
        returned_status = Status_order.objects.filter(status__icontains="مرتجع").first()
        if returned_status:
            order.status = returned_status
            order.save()
            messages.success(request, "تم إرجاع الطلب بنجاح")
        else:
            messages.error(request, "لم يتم العثور على حالة 'مرتجع'")

    elif action == 'delete' and user_role == 'manager':
        order.delete()
        messages.success(request, "تم حذف الطلب نهائياً")
        return redirect('orders')

    elif action == 'edit_payment' and user_role == 'manager':
        new_method = request.POST.get('payment_method')
        if new_method in ['cash', 'visa']:
            order.payment_method = new_method
            order.save()
            messages.success(request, "تم تحديث طريقة الدفع")

    return redirect('order_detail', order_id=order.id)

# ================= INVENTORY MANAGEMENT =================

@role_required('manager')
def menu_management(request, product_id=None):
    product = get_object_or_404(Product, id=product_id) if product_id else None
    if request.method == 'POST':
        if 'delete' in request.POST and product:
            product.delete()
            messages.success(request, 'تم حذف المنتج!')
            return redirect('menu_management')
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم حفظ المنتج بنجاح!')
            return redirect('menu_management')
    else:
        form = ProductForm(instance=product)
    return render(request, 'pos/menu_management.html', {'form': form, 'products': Product.objects.all(), 'editing_product': product})

def inventory_management(request):
    items = InventoryItem.objects.all().order_by('name')
    low_stock_count = items.filter(quantity__lte=F('min_limit')).count()
    inventory_value = sum(item.quantity * item.unit_cost for item in items)
    
    category_filter = request.GET.get('category')
    if category_filter and category_filter != 'all':
        items = items.filter(category_id=category_filter)

    context = {
        'items': items,
        'categories': IngredientCategory.objects.all(),
        'units': Unit_choices.objects.all(),
        'suppliers': Supplier.objects.all(),
        'sizes': Size_choices.objects.all(),
        'colors': Colors_choices.objects.all(),
        'total_items_count': items.count(),
        'low_stock_count': low_stock_count,
        'inventory_value': inventory_value,
        'selected_category': category_filter,
    }
    return render(request, 'pos/inventory_management.html', context)

@require_POST
def add_inventory_item(request):
    try:
        supplier_id = request.POST.get('Supplier')
        sup_phone = request.POST.get('supplier_phone_input')
        new_sup_name = request.POST.get('new_supplier_name')

        if not supplier_id and sup_phone and new_sup_name:
            supplier_obj, created = Supplier.objects.get_or_create(
                mobil=sup_phone, defaults={'name': new_sup_name}
            )
            supplier_id = supplier_obj.id

        quantity = Decimal(request.POST.get('quantity') or 0)
        supply_cost = Decimal(request.POST.get('supply_cost') or 0)
        paid_amount = Decimal(request.POST.get('paid_amount') or 0)
        total_amount = quantity * supply_cost
        remaining_amount = total_amount - paid_amount

        item = InventoryItem.objects.create(
            name=request.POST.get('name'),
            category_id=request.POST.get('category'),
            unit_id=request.POST.get('unit'),
            quantity=quantity,
            min_limit=Decimal(request.POST.get('min_limit') or 0),
            unit_cost=Decimal(request.POST.get('unit_cost') or 0),
            supply_cost=supply_cost,
            Supplier_id=supplier_id or None,
            size_id=request.POST.get('size') or None,
            color_id=request.POST.get('color') or None,
        )

        if item.Supplier and (total_amount > 0 or paid_amount > 0):
            SupplyLog.objects.create(
                supplier=item.Supplier, item=item, quantity_added=quantity,
                cost_at_time=supply_cost, total_amount=total_amount,
                paid_amount=paid_amount, remaining_amount=remaining_amount
            )

        messages.success(request, 'تم إضافة الصنف وتحديث سجلات المورد.')
        return redirect('inventory_management')
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('inventory_management')

@require_POST
def update_inventory_quantity(request):
    item_id = request.POST.get('item_id')
    amount_raw = request.POST.get('amount', '0').strip()
    action = request.POST.get('action')
    try:
        amount_clean = "".join(filter(lambda x: x in "0123456789.", amount_raw))
        amount = Decimal(amount_clean)
        item = get_object_or_404(InventoryItem, id=item_id)

        if action == 'add':
            item.quantity += amount
        elif action == 'subtract':
            if item.quantity < amount:
                return JsonResponse({'status': 'error', 'message': 'المخزون لا يكفي'}, status=400)
            item.quantity -= amount
        
        item.save()
        return JsonResponse({'status': 'success', 'message': 'تم التحديث بنجاح'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ================= SUPPLIER MANAGEMENT =================

def supplies_management(request):
    if request.method == "POST":
        name = request.POST.get('name')
        mobil = request.POST.get('mobil') 
        address = request.POST.get('address', '')
        if name and mobil:
            Supplier.objects.create(name=name, mobil=mobil, address=address)
            messages.success(request, f"تم إضافة المورد {name}")
            return redirect('supplies_management')

    suppliers = Supplier.objects.all().order_by('-id')
    total_debts = SupplyLog.objects.aggregate(total=Sum('remaining_amount'))['total'] or 0
    return render(request, 'pos/supplies_management.html', {'suppliers': suppliers, 'total_debts': total_debts})

def delete_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    messages.warning(request, "تم حذف المورد")
    return redirect('supplies_management')

@require_POST
def pay_supplier_debt(request):
    supplier_id = request.POST.get('supplier_id')
    amount_raw = request.POST.get('amount', '0')
    try:
        amount_paid = Decimal(amount_raw)
        if amount_paid <= 0:
            messages.error(request, "مبلغ غير صحيح")
            return redirect('supplies_management')

        supplier = Supplier.objects.get(id=supplier_id)
        SupplyLog.objects.create(
            supplier=supplier, item=None, quantity_added=0, cost_at_time=0,
            total_amount=0, paid_amount=amount_paid, remaining_amount=-amount_paid 
        )
        messages.success(request, f"تم سداد {amount_paid} ج.م")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('supplies_management')

def get_supplier_logs(request, supplier_id):
    try:
        # استخدام filter لضمان العمل حتى لو لم يتم تعريف related_name
        logs = SupplyLog.objects.filter(supplier_id=supplier_id).order_by('-id')
        logs_list = []
        for log in logs:
            # محاولة جلب التاريخ من created_at أو date
            dt = getattr(log, 'created_at', getattr(log, 'date', timezone.now()))
            logs_list.append({
                'date': dt.strftime('%Y-%m-%d'),
                'item_name': log.item.name if log.item else "سداد نقدي / دفعة حساب",
                'total_amount': float(log.total_amount or 0),
                'paid_amount': float(log.paid_amount or 0),
                'remaining_amount': float(log.remaining_amount or 0),
            })
        return JsonResponse({'logs': logs_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_supplier_by_phone(request):
    phone = request.GET.get('phone')
    supplier = Supplier.objects.filter(mobil=phone).first() 
    if supplier:
        return JsonResponse({'found': True, 'id': supplier.id, 'name': supplier.name})
    return JsonResponse({'found': False})

# ================= REPORTS & EMPLOYEES =================

def sales_reports(request):
    now = timezone.now()
    filter_type = request.GET.get('range', 'today')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    staff_id = request.GET.get('staff_id', 'all')
    
    query = Q()
    if filter_type == 'today': query &= Q(created_at__date=now.date())
    elif filter_type == 'week': query &= Q(created_at__gte=now - timedelta(days=7))
    elif filter_type == 'month': query &= Q(created_at__month=now.month)
    elif filter_type == 'custom' and start_date and end_date:
        query &= Q(created_at__date__gte=start_date, created_at__date__lte=end_date)

    if not (hasattr(request.user, 'role') and request.user.role == 'manager'):
        query &= Q(user=request.user)
    elif staff_id != 'all':
        query &= Q(user_id=staff_id)

    report_orders = Order.objects.filter(query)
    best_sellers = OrderItem.objects.filter(order__in=report_orders).values('product__name').annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]

    context = {
        'stats': {
            'total_sales': report_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'orders_count': report_orders.count(),
            'avg_order': report_orders.aggregate(Avg('total_price'))['total_price__avg'] or 0,
        },
        'best_sellers': best_sellers,
        'recent_orders': report_orders.order_by('-created_at')[:10],
        'is_manager': getattr(request.user, 'role', '') == 'manager',
        'staff_members': User.objects.all() if getattr(request.user, 'role', '') == 'manager' else None,
        'filter_type': filter_type,
    }
    return render(request, 'pos/sales_reports.html', context)

def employees_management(request):
    return render(request, 'pos/employees_management.html')