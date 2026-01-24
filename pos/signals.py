from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from decimal import Decimal
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

    # تحويل الحالات لنصوص للمقارنة بأمان
    new_status_text = str(new_status_obj.status) if new_status_obj and hasattr(new_status_obj, 'status') else ""
    old_status_text = str(old_status_obj.status) if old_status_obj and hasattr(old_status_obj, 'status') else ""

    # 1. تحديث حالة قطعة البدلة (RentalItem) لتطابق حالة الطلب
    # نستخدم update لتجنب استدعاء السجنالات الخاصة بـ RentalItem ومنع اللوب اللانهائي
    if rental_piece.status != new_status_obj:
        RentalItem.objects.filter(pk=rental_piece.pk).update(status=new_status_obj)

    # 2. منطق العمليات عند تغير الحالة أو إنشاء طلب جديد
    if old_status_text != new_status_text or created:
        
        # --- [ أ ] الانتقال من (أي حالة/جديد) إلى (محجوز) أو (نفذه) ---
        if new_status_text in ["محجوز", "نفذه"] and (created or old_status_text not in ["محجوز", "نفذه"]):
            # خصم الكمية من المخزن الأساسي
            if inventory_item and inventory_item.quantity > 0:
                inventory_item.quantity -= 1
                inventory_item.save()
            
            # تحديث إحصائيات قطعة الإيجار
            # التحويل لـ Decimal هنا هو حل المشكلة التي ظهرت لك
            price_to_add = Decimal(str(instance.total_price or 0))
            
            rental_piece.rental_count += 1
            rental_piece.profit += price_to_add
            rental_piece.save()

        # --- [ ب ] الانتقال من (محجوز/نفذه) إلى (متوفر) - أي استرجاع البدلة ---
        elif new_status_text == "متوفر":
            if old_status_text in ["محجوز", "نفذه"]:
                # إعادة القطعة للكمية المتاحة في المخزن
                if inventory_item:
                    inventory_item.quantity += 1
                    inventory_item.save()

# --- [ ج ] المزامنة العكسية: من RentalItem إلى RentalOrder ---
@receiver(post_save, sender=RentalItem)
def sync_item_to_order(sender, instance, **kwargs):
    """إذا تغيرت حالة البدلة يدوياً، يتم تحديث آخر طلب مرتبطة به"""
    last_order = RentalOrder.objects.filter(item=instance).order_by('-id').first()
    
    if last_order and last_order.status != instance.status:
        # نستخدم update لتجنب إعادة تشغيل سجنال RentalOrder (منع Infinite Loop)
        RentalOrder.objects.filter(pk=last_order.pk).update(status=instance.status)