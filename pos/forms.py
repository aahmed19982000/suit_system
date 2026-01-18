# forms.py
from django import forms
from .models import Product

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
