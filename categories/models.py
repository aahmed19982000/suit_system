from django.db import models
from django.utils import timezone
from django.conf import settings

class Site(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم الموقع")
    start_date = models.DateField(null=True, blank=True, verbose_name="تاريخ البدء")  
    number_of_days = models.PositiveIntegerField(verbose_name="عدد ايام الفارق")
    site_link = models.URLField(max_length=200, verbose_name="رابط الموقع")
    sitemaps_links = models.URLField(verbose_name="روابط الـ sitemap", help_text="ضع كل رابط في سطر جديد")
   


    def __str__(self):  
        return self.name

class Article_type_U_N(models.Model):
    type = models.CharField(max_length=100, verbose_name="(تحديث ام جديد)نوع المقال")
    number_of_article = models.PositiveIntegerField(verbose_name="عدد المقالات المسموح بها")

    def __str__(self):
        return self.type

class Article_type_W_R_A_B(models.Model):
    type = models.CharField(max_length=100, verbose_name="(تحذير / تقييم/تعليمي/افضل شركات)نوع المقال")
    number_of_article = models.PositiveIntegerField(verbose_name="عدد المقالات المسموح بها")

    def __str__(self):
        return self.type

WEEKDAYS = [
    (5, 'السبت'),
]
class Official_holiday(models.Model):
    holiday_day = models.IntegerField(choices=WEEKDAYS, default=5, verbose_name="اليوم الرسمي للإجازة")  

class CustomHoliday(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستخدم")
    date = models.DateField(verbose_name="تاريخ الإجازة")
    reason = models.CharField(max_length=255, blank=True, null=True, verbose_name="سبب الإجازة (اختياري)")

    class Meta:
        verbose_name = "إجازة مخصصة"
        verbose_name_plural = "إجازات مخصصة"
        unique_together = ('user', 'date')  

    def __str__(self):
        return f"{self.user.username} - {self.date}"
    

class contract_details(models.Model):
    details = models.CharField(verbose_name="تفاصيل العقد")

    def __str__(self):
        return self.details[:50]  
    

class contract_duration(models.Model):
    duration = models.CharField(max_length=100, verbose_name="مدة العقد")
    number_of_duration = models.DecimalField(max_digits=4,decimal_places=2,verbose_name="رقم مدة العقد بالسنوات")

    def __str__(self):
        return self.duration
    

class Category_products(models.Model):
    category = models.CharField (max_length=100, verbose_name="قسم المنيو")

    def __str__(self):
        return self.category
    
 
class Status_order(models.Model):
    status = models.CharField (max_length=100, verbose_name="حالة الطلب")

    def __str__(self):
        return self.status
    

class IngredientCategory(models.Model):
    category = models.CharField (max_length=100, verbose_name="اصناف المخزن ")
    def __str__(self):
        return self.category
    

class Unit_choices(models.Model):
    unit = models.CharField (max_length=100, verbose_name="وحدات التخزين")
    def __str__(self):
        return self.unit