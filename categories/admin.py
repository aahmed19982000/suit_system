from django.contrib import admin
from .models import Site, Article_type_U_N ,Article_type_W_R_A_B, Official_holiday, CustomHoliday, contract_details, contract_duration ,Category_products , Status_order , Unit_choices,IngredientCategory
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name','number_of_days','start_date','site_link']

@admin.register(Article_type_U_N)
class Article_type_U_NAdmin(admin.ModelAdmin):
    list_display = ['type','number_of_article']

@admin.register(Article_type_W_R_A_B)
class Article_type_W_R_A_BAdmin(admin.ModelAdmin):
    list_display = ['type','number_of_article']

@admin.register(Official_holiday)
class Official_holidayAdmin(admin.ModelAdmin):
    list_display = ['holiday_day']

@admin.register(CustomHoliday)
class CustomHolidayAdmin(admin.ModelAdmin):
    list_display = ['user','reason','date']

@admin.register(contract_details)
class contract_detailsAdmin(admin.ModelAdmin):
    list_display = ['details']

@admin.register(contract_duration)
class contract_durationAdmin(admin.ModelAdmin):
    list_display = ['duration','number_of_duration']


@admin.register(Category_products)
class Category(admin.ModelAdmin):
    list_display = ['category']


@admin.register(Status_order)
class status(admin.ModelAdmin):
    list_display = ['status']



@admin.register(Unit_choices)
class status(admin.ModelAdmin):
    list_display = ['unit']

@admin.register(IngredientCategory)
class status(admin.ModelAdmin):
    list_display = ['category']
