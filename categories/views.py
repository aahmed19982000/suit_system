from django.shortcuts import render, get_object_or_404, redirect
from .models import Site, Official_holiday ,CustomHoliday 
from accounts.decorators import role_required
from .forms import SiteForm ,Official_holidayForm, CustomHolidayForm

# عرض المواقع + إنشاء موقع جديد
@role_required('manager')
def site(request):
    categories = Site.objects.all()
    form = SiteForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('site')  

    return render(request, 'Categories/site.html', {
        'categories': categories,
        'form': form
    })

# تعديل موقع
@role_required('manager')
def edit_site(request, site_id):
    site_instance = get_object_or_404(Site, id=site_id)
    form = SiteForm(request.POST or None, instance=site_instance)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('site')  

    return render(request, 'categories/site.html', {
        'form': form,
        'categories': Site.objects.all() 
    })

# حذف موقع
@role_required('manager')
def delete_site(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    site.delete()
    return redirect('site')

#اجازات الموظفين 
@role_required('manager')
def holiday(request):
    official_holidays = Official_holiday.objects.all()
    custom_holidays = CustomHoliday.objects.all()

    official_form = Official_holidayForm(request.POST or None, prefix="official")
    custom_form = CustomHolidayForm(request.POST or None, prefix="custom")

    if request.method == 'POST':
        if 'submit_official' in request.POST and official_form.is_valid():
            official_form.save()
            return redirect('holiday')

        elif 'submit_custom' in request.POST and custom_form.is_valid():
            custom_form.save()
            return redirect('holiday')

    return render(request, 'categories/holiday.html', {
        'official_holidays': official_holidays,
        'custom_holidays': custom_holidays,
        'official_form': official_form,
        'custom_form': custom_form,
    })