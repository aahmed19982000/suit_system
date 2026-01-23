from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import RentalOrder, RentalItem

@receiver(pre_save, sender=RentalOrder)
def capture_old_status(sender, instance, **kwargs):
    """الاحتفاظ بالحالة القديمة قبل الحفظ للمقارنة"""
    if instance.pk:
        try:
            # جلب الحالة من قاعدة البيانات قبل التحديث
            instance._old_status = RentalOrder.objects.get(pk=instance.pk).status
        except RentalOrder.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=RentalOrder)
def sync_rental_logic(sender, instance, created, **kwargs):
    """تنسيق الحسابات، المخزن، وحالة القطع"""
    rental_piece = instance.item
    inventory_item = rental_piece.item
    
    new_status_obj = instance.status
    old_status_obj = getattr(instance, '_old_status', None)

    # تحويل الحالات لنصوص للمقارنة بناءً على حقل status في موديل Rental_status_choices
    new_status_text = new_status_obj.status if new_status_obj else ""
    old_status_text = old_status_obj.status if old_status_obj else ""

    # 1. تحديث حالة قطعة البدلة لتطابق الطلب دائماً
    if rental_piece.status != new_status_obj:
        rental_piece.status = new_status_obj
        rental_piece.save()

    # 2. منطق العمليات عند تغير الحالة أو إنشاء طلب جديد
    if old_status_text != new_status_text or created:
        
        # --- [ أ ] الانتقال من (متوفر) إلى (محجوز) ---
        if new_status_text == "محجوز" and (created or old_status_text == "متوفر"):
            # خصم الكمية من المخزن
            inventory_item.quantity -= 1
            
            # زيادة عداد الحجز
            rental_piece.rental_count += 1
            inventory_item.total_rentals += 1
            
            # إضافة الربح (يُحسب عند الحجز لضمان تسجيل القيمة)
            rental_piece.profit += instance.total_price
            inventory_item.total_profit += instance.total_price
            
            # حفظ التغييرات
            inventory_item.save()
            rental_piece.save()

        # --- [ ب ] الانتقال من (متوفر) إلى (نفذه) مباشرة ---
        elif new_status_text == "نفذه" and (created or old_status_text == "متوفر"):
            # خصم الكمية
            inventory_item.quantity -= 1
            # زيادة العداد
            rental_piece.rental_count += 1
            inventory_item.total_rentals += 1
            # إضافة الربح
            rental_piece.profit += instance.total_price
            inventory_item.total_profit += instance.total_price
            
            inventory_item.save()
            rental_piece.save()

        # --- [ ج ] الانتقال من (محجوز) أو (نفذه) إلى (متوفر) ---
        elif new_status_text == "متوفر":
            if old_status_text in ["محجوز", "نفذه"]:
                # إعادة القطعة للكمية المتاحة في المخزن
                inventory_item.quantity += 1
                inventory_item.save()

# --- [ د ] المزامنة العكسية: من RentalItem إلى RentalOrder ---
@receiver(post_save, sender=RentalItem)
def sync_item_to_order(sender, instance, **kwargs):
    """إذا تغيرت حالة البدلة يدوياً من صفحتها، يتم تحديث آخر طلب مرتبطة به"""
    last_order = RentalOrder.objects.filter(item=instance).order_by('-id').first()
    
    if last_order and last_order.status != instance.status:
        # نستخدم update لتجنب إعادة تشغيل السجنالات (تجنب اللوب اللانهائي)
        RentalOrder.objects.filter(pk=last_order.pk).update(status=instance.status)