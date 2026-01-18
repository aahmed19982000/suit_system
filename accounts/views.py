from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from accounts.decorators import role_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import logging



# استخدام موحّد للموديل
User = get_user_model()



# ✅ إنشاء مستخدم
@role_required('manager')
def signup_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name  = request.POST.get('last_name')
        username   = request.POST.get('username')
        email      = request.POST.get('email')
        password   = request.POST.get('password')
        confirm    = request.POST.get('confirm')
        job_title  = request.POST.get('job_title')
        role       = request.POST.get('role')  

        if password != confirm:
            messages.error(request, 'كلمة المرور غير متطابقة.')
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'اسم المستخدم موجود بالفعل.')
            return redirect('signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.job_title = job_title
        user.save()
        

        role = 'Managers' if role == 'manager' else 'Employees'
       
        messages.success(request, 'تم إنشاء الحساب بنجاح!')
        return redirect('signup')

    return render(request, 'accounts/signup.html')

# ✅ تسجيل الدخول
def t_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'تم تسجيل الدخول بنجاح.')

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            elif user.role == 'manager':
                 return redirect('dashboard')
            elif user.role == 'designer':
                 return redirect('dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')

    return render(request, 'accounts/login.html')

# ✅ تسجيل الخروج
def logout_view(request):
    logout(request)
    return redirect('t_login')

# ✅ عرض الموظفين
@role_required('manager')
def employee_list(request):
    employees = User.objects.all()  # أو Users.objects.all() لو انت معرف الموديل كده
    print(employees)  # للتأكد في Console
    return render(request, 'pos/employees_management.html', {'employees': employees})
# ✅ حذف الموظف
@role_required('manager')
def delete_employee(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user.delete()
        messages.success(request, 'تم حذف الموظف بنجاح.')
        return redirect('employee_list')

    messages.error(request, 'حدث خطأ أثناء الحذف.')
    return redirect('employee_list')

# ✅ صفحة للمديرين فقط
def manager_dashboard(request):
    if request.user.profile.role != 'manager':
        return redirect('no_permission')  # أو ترجع رسالة ممنوع الوصول
    return render(request, 'home/manager.html')

def no_permission(request):
    return render(request, 'home/no_permission.html')




logger = logging.getLogger(__name__)

# جعل الإشعار مقروء
@require_POST
@login_required
def mark_notification_as_read(request, notification_id):
    try:
        note = Notification.objects.get(id=notification_id, user=request.user)
        note.is_read = True
        note.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        logger.warning(f"إشعار غير موجود - ID: {notification_id}, User: {request.user}")
        return JsonResponse({'success': False, 'error': 'الإشعار غير موجود'}, status=404)

# حذف الإشعار
@require_POST
@login_required
def delete_notification(request, notification_id):
    try:
        note = Notification.objects.get(id=notification_id, user=request.user)
        note.delete()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        logger.warning(f"محاولة حذف إشعار غير موجود - ID: {notification_id}, User: {request.user}")
        return JsonResponse({'success': False, 'error': 'الإشعار غير موجود'}, status=404)
