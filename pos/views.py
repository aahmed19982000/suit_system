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
from django.db import transaction
from django.db.models import F
import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

# استيراد الموديلات
from .models import (
    Product, Customer, Supplier, SupplyLog, Order, 
    OrderItem, Status_order, InventoryItem, IngredientCategory ,RentalOrder
)
from .forms import ProductForm , RentalOrderForm
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
    # بدلاً من المنتجات، سنجلب أصناف المخزن المتوفرة
    # سنفترض أنك تريد عرض الأصناف التي كميتها أكبر من 0 أو كلها
    products = InventoryItem.objects.all() 
    
    # جلب تصنيفات المواد الخام/المخزن
    categories = IngredientCategory.objects.all() 
    
    return render(request, 'pos/pos_page.html', {
        'products': products, 
        'categories': categories
    })



@csrf_exempt
@login_required
def cash_checkout(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # --- الحالة الأولى: منطق تأجير البدلة (الجديد) ---
            if data.get('is_rental'):
                item_name = data.get('item_name')
                price = data.get('price', 0)
                deposit = data.get('deposit', 0)
                sizes = data.get('sizes', 'غير محدد')
                notes = data.get('notes', 'لا يوجد')
                dates = f"من {data.get('start_date')} إلى {data.get('end_date')}"

                with transaction.atomic():
                    # إنشاء الطلب كعملية تأجير
                    order = Order.objects.create(
                        user=request.user,
                        payment_method='cash',
                        total_price=Decimal(str(price)),
                        # نضع كل التفاصيل في حقل الوصف أو ملاحظات الطلب إذا كان متاحاً
                        # هنا نستخدم f-string لجمع البيانات المطلوبة للطباعة والسجل
                    )
                    
                    # ملاحظة: إذا كان لديك حقل ملاحظات في موديل Order يفضل تخزينه فيه
                    # order.notes = f"تأجير: {item_name} | مقاسات: {sizes} | تأمين: {deposit} | فترة: {dates} | ملاحظات إضافية: {notes}"
                    # order.save()

                    return JsonResponse({
                        'status': 'success', 
                        'order_id': order.id,
                        'message': 'تم تسجيل عملية التأجير بنجاح'
                    })

            # --- الحالة الثانية: منطق البيع المباشر (الكود الأصلي الخاص بك) ---
            cart = data.get('cart', [])
            total = data.get('total')
            order_type = data.get('order_type')
            cust_data = data.get('customer_data')

            if not cart:
                return JsonResponse({'status': 'error', 'message': 'السلة فارغة!'}, status=400)

            with transaction.atomic():
                # 1. معالجة بيانات العميل
                customer_obj = None
                if order_type == 'delivery' and cust_data:
                    customer_obj, created = Customer.objects.get_or_create(
                        mobil=cust_data['phone'],
                        defaults={'name': cust_data['name'], 'address': cust_data['address']}
                    )
                    customer_obj.number_of_orders = F('number_of_orders') + 1
                    customer_obj.save()

                # 2. إنشاء الطلب الرئيسي
                order = Order.objects.create(
                    user=request.user,
                    customer=customer_obj,
                    payment_method='cash',
                    total_price=Decimal(str(total)),
                )

                # 3. معالجة عناصر السلة والخصم من المخزن
                for item in cart:
                    inv_item = InventoryItem.objects.select_for_update().get(id=item['id'])
                    qty_sold = Decimal(str(item['qty']))

                    if inv_item.quantity < qty_sold:
                        return JsonResponse({
                            'status': 'error', 
                            'message': f'الكمية المتاحة من {inv_item.name} غير كافية (المتاح: {inv_item.quantity})'
                        }, status=400)

                    inv_item.quantity -= qty_sold
                    inv_item.save()

                    OrderItem.objects.create(
                        order=order,
                        product_id=inv_item.id, 
                        price=Decimal(str(item['price'])),
                        quantity=qty_sold
                    )

                return JsonResponse({
                    'status': 'success', 
                    'order_id': order.id,
                    'message': 'تم تسجيل الطلب وتحديث المخزن'
                })

        except InventoryItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'أحد الأصناف غير موجود في المخزن'}, status=404)
        except Exception as e:
            print(f"Checkout Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'حدث خطأ أثناء المعالجة'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)

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

        # إنشاء المورد الجديد إذا لازم
        if not supplier_id and sup_phone and new_sup_name:
            supplier_obj, created = Supplier.objects.get_or_create(
                mobil=sup_phone, defaults={'name': new_sup_name}
            )
            if created:
                supplier_obj.name = new_sup_name
                supplier_obj.save()
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
            profit=Decimal(request.POST.get('profit') or 0),
            is_rental=request.POST.get('is_rental') == 'on',
        )

        if item.Supplier and (total_amount > 0 or paid_amount > 0):
            SupplyLog.objects.create(
                supplier=item.Supplier,
                item=item,
                quantity_added=quantity,
                cost_at_time=supply_cost,
                total_amount=total_amount,
                paid_amount=paid_amount,
                remaining_amount=remaining_amount
            )

        messages.success(request, 'تم إضافة الصنف وتحديث سجلات المورد.')
        return redirect('inventory_management')

    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('inventory_management')


@require_POST
def update_inventory_quantity(request):
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        
        # دالة تنظيف الأرقام
        def clean_decimal(val):
            if not val: return Decimal('0')
            clean_val = "".join(filter(lambda x: x in "0123456789.", str(val)))
            return Decimal(clean_val) if clean_val else Decimal('0')

        try:
            qty_added = clean_decimal(request.POST.get('quantity_added'))
            paid_amount = clean_decimal(request.POST.get('paid_amount'))
            
            item = get_object_or_404(InventoryItem, id=item_id)

            if qty_added > 0:
                # 1. تحديث الكمية في المخزن (InventoryItem)
                item.quantity += qty_added
                item.save()

                # 2. تسجيل العملية في سجل التوريد (SupplyLog)
                # الموديل سيتكفل بحساب الإجمالي والديون في دالة save() الخاصة به
                if item.Supplier:
                    SupplyLog.objects.create(
                        supplier=item.Supplier,  # تأكدنا أنها بحرف صغير كما في الموديل
                        item=item,
                        quantity_added=qty_added,
                        cost_at_time=item.supply_cost, # السعر المسجل في الصنف
                        paid_amount=paid_amount
                    )
                    # ملاحظة: مديونية المورد في موديلك تُحسب عبر @property (Sum) 
                    # لذا لا حاجة لتحديث حقل debt يدوياً إذا لم يكن موجوداً كحقل ثابت.

                return JsonResponse({'status': 'success', 'message': 'تم تحديث المخزون وسجل المورد بنجاح'})
            
            return JsonResponse({'status': 'error', 'message': 'يرجى إدخال كمية صحيحة'}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطأ: {str(e)}'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'طلب غير مسموح'}, status=405)# ================= SUPPLIER MANAGEMENT =================

def supplies_management(request):
    if request.method == "POST":
        name = request.POST.get('name')
        mobil = request.POST.get('mobil') 
        address = request.POST.get('address', '')
        if name and mobil:
            Supplier.objects.create(name=name, mobil=mobil, address=address)
            messages.success(request, f"تم إضافة المورد {name} بنجاح")
            return redirect('supplies_management')

    suppliers = Supplier.objects.all().order_by('-id')
    # حساب إجمالي المديونية من كافة الموردين
    total_debts = SupplyLog.objects.aggregate(total=Sum('remaining_amount'))['total'] or 0
    # حساب إجمالي المدفوعات
    total_spending = SupplyLog.objects.aggregate(total=Sum('paid_amount'))['total'] or 0
    
    context = {
        'suppliers': suppliers, 
        'total_debts': total_debts,
        'total_spending': total_spending
    }
    return render(request, 'pos/supplies_management.html', context)


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
            messages.error(request, "يرجى إدخال مبلغ صحيح أكبر من الصفر.")
            return redirect('supplies_management')

        supplier = get_object_or_404(Supplier, id=supplier_id)
        
        # تسجيل عملية السداد في جدول SupplyLog
        # نضع قيم صفرية للكمية والتكلفة لأنها عملية سداد نقدي فقط
        SupplyLog.objects.create(
            supplier=supplier,
            item=None, 
            quantity_added=0,
            cost_at_time=0,
            total_amount=0,
            paid_amount=amount_paid,
            remaining_amount=-amount_paid # القيمة السالبة هنا تخفض إجمالي الدين
        )
        
        messages.success(request, f"تم تسجيل سداد مبلغ {amount_paid} ج.م للمورد {supplier.name}")
    except (InvalidOperation, ValueError):
        messages.error(request, "خطأ في صيغة المبلغ المدخل.")
    except Exception as e:
        messages.error(request, f"حدث خطأ غير متوقع: {str(e)}")
        
    return redirect('supplies_management')

def get_supplier_logs(request, supplier_id):
    try:
        # تأكد من استيراد الموديلات بشكل صحيح في بداية الملف
        supplier = get_object_or_404(Supplier, id=supplier_id)
        logs = supplier.supply_history.all().order_by('-created_at')
        
        logs_list = []
        for log in logs:
            logs_list.append({
                'id': log.id,
                'date': log.created_at.strftime('%Y-%m-%d %I:%M %p'),
                'type': 'payment' if not log.item else 'supply',
                'item_name': log.item.name if log.item else "سداد مالي",
                'quantity': float(log.quantity_added or 0),
                'total_amount': float(log.total_amount or 0),
                'paid_amount': float(log.paid_amount or 0),
                'remaining': float(log.remaining_amount or 0), # أضفنا المتبقي هنا
            })
        return JsonResponse({'status': 'success', 'logs': logs_list})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

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


# دالة حذف سجل توريد أو سداد فردي من كشف الحساب
@require_POST
def delete_supply_log(request, log_id):
    log = get_object_or_404(SupplyLog, id=log_id)
    supplier_id = log.supplier.id
    log.delete()
    messages.success(request, "تم حذف السجل وتحديث المديونية تلقائياً")
    return redirect('supplies_management')

# دالة تعديل مبلغ مدفوع في سجل معين
@require_POST
def edit_supply_log(request, log_id):
    log = get_object_or_404(SupplyLog, id=log_id)
    new_amount = request.POST.get('amount')
    try:
        log.paid_amount = Decimal(new_amount)
        # سيقوم الموديل بإعادة حساب المتبقي في دالة save()
        log.save()
        messages.success(request, "تم تعديل السجل بنجاح")
    except Exception as e:
        messages.error(request, f"خطأ في التعديل: {str(e)}")
    return redirect('supplies_management')



# 1. دالة تعديل بيانات الصنف (الاسم والأسعار)
def edit_inventory_item(request):
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        item = get_object_or_404(InventoryItem, id=item_id)
        
        item.name = request.POST.get('name')
        item.unit_cost = request.POST.get('unit_cost')
        item.supply_cost = request.POST.get('supply_cost')
        item.save()
        
        return JsonResponse({'status': 'success'})

# 2. دالة حذف الصنف
def delete_inventory_item(request):
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        item = get_object_or_404(InventoryItem, id=item_id)
        item.delete()
        return JsonResponse({'status': 'success'})
    

@require_POST
def create_customer_ajax(request):
    try:
        data = json.loads(request.body)

        customer = Customer.objects.create(
            name=data.get('name'),
            mobil=data.get('phone'),
            address=data.get('address', '')
        )

        return JsonResponse({
            'status': 'success',
            'id': customer.id,
            'name': customer.name
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


def pos_rental_page(request):
    # جلب العناصر المتاحة للإيجار فقط والتي بها مخزون
    products = InventoryItem.objects.filter(is_rental=True, quantity__gt=0)
    customers = Customer.objects.all().order_by('-id') # ترتيب الأحدث أولاً
    return render(request, 'pos/rental_pos.html', {
        'products': products,
        'customers': customers
    })

def rental_checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # 1. التأكد من وجود البيانات الأساسية
            customer_id = data.get('customer_id')
            item_id = data.get('item_id')
            if not customer_id or not item_id:
                return JsonResponse({'status': 'error', 'message': 'بيانات العميل أو البدلة ناقصة'}, status=400)

            customer = get_object_or_404(Customer, pk=customer_id)
            item = get_object_or_404(InventoryItem, pk=item_id)

            # 2. تحويل وتجهيز الأرقام مع التعامل مع القيم الفارغة
            total_price = float(data.get('total_price') or 0)
            deposit_amount = float(data.get('deposit') or 0)

            # 3. تحويل التواريخ
            rental_date = datetime.strptime(data.get('rental_date'), "%Y-%m-%d").date()
            return_date = datetime.strptime(data.get('return_date'), "%Y-%m-%d").date()

            # 4. إنشاء سجل الحجز
            rental_order = RentalOrder.objects.create(
                customer=customer,
                item=item,
                rental_date=rental_date,
                return_date=return_date,
                total_price=total_price,
                deposit_amount=deposit_amount,
                notes=data.get('notes', ''),
                status='booked'
            )

            # 5. (اختياري) تحديث الكمية في المخزن
            # item.quantity -= 1
            # item.save()

            return JsonResponse({
                'status': 'success', 
                'rental_order_id': rental_order.id,
                'message': 'تم الحجز بنجاح'
            })

        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'خطأ في تنسيق البيانات الرقمية أو التواريخ'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'طلب غير صالح'}, status=405)


def all_rental_items(request):
    # جلب العناصر المخصصة للإيجار فقط
    items = InventoryItem.objects.filter(is_rental=True).order_by('-id')
    return render(request, 'pos/rental_items_list.html', {'items': items})