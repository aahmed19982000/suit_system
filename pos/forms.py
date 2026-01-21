# forms.py
from django import forms
from .models import Product , RentalOrder

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'available', 'description','Category']  # الحقول اللي تظهر في الفورم
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المنتج'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'السعر'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'الوصف', 'rows': 3}),
        }
        labels = {
            'name': 'اسم المنتج',
            'price': 'السعر',
            'available': 'متاح',
            'description': 'الوصف',
        }

class RentalOrderForm(forms.ModelForm):
    class Meta:
        model = RentalOrder
        fields = ['customer', 'item', 'rental_date', 'return_date', 'status']  # الحقول اللي تظهر في الفورم
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'item': forms.Select(attrs={'class': 'form-control'}),
            'rental_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'customer': 'العميل',
            'item': 'العنصر',
            'rental_date': 'تاريخ الإيجار',
            'return_date': 'تاريخ الإرجاع',
            'status': 'الحالة',
        }