from django import forms
from .models import Site, Official_holiday, CustomHoliday

class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ['name', 'number_of_days', 'start_date','site_link']

class Official_holidayForm(forms.ModelForm):
    class Meta:
        model = Official_holiday
        fields = ['holiday_day']

class CustomHolidayForm(forms.ModelForm):
    class Meta:
        model = CustomHoliday
        fields = ['user','reason','date']