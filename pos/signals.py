from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import RentalOrder, RentalItem

# --- حفظ الحالة القديمة للـ RentalOrder قبل التحديث
@receiver(pre_save, sender=RentalOrder)
def rentalorder_capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = RentalOrder.objects.get(pk=instance.pk).status
        except RentalOrder.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

# --- حفظ الحالة القديمة للـ RentalItem قبل التحديث
@receiver(pre_save, sender=RentalItem)
def rentalitem_capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = RentalItem.objects.get(pk=instance.pk).status
        except RentalItem.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

# --- تزامن من RentalOrder → RentalItem
@receiver(post_save, sender=RentalOrder)
def rentalorder_to_item(sender, instance, created, **kwargs):
    rental_item = instance.item
    new_status = instance.status
    old_status = getattr(instance, '_old_status', None)

    # التأكد من وجود حالة جديدة وحالة قديمة للمقارنة
    new_status_text = str(new_status.status) if new_status else ""
    old_status_text = str(old_status.status) if old_status else ""

    # لو الحالة اتغيرت أو الطلب جديد
    if created or old_status_text != new_status_text:
        # 1️⃣ تحديث حالة البدلة RentalItem لتطابق حالة الطلب
        if rental_item.status != new_status:
            RentalItem.objects.filter(pk=rental_item.pk).update(status=new_status)

        # 2️⃣ تحديث عدد مرات الإيجار والربح عند الحجز أو التنفيذ
        if new_status_text in ["محجوز", "نفذه"] and (created or old_status_text not in ["محجوز", "نفذه"]):
            new_rental_count = rental_item.rental_count + 1
            new_profit = rental_item.profit + (instance.total_price or 0)
            RentalItem.objects.filter(pk=rental_item.pk).update(
                rental_count=new_rental_count,
                profit=new_profit
            )

# --- تزامن من RentalItem → آخر RentalOrder
@receiver(post_save, sender=RentalItem)
def rentalitem_to_order(sender, instance, **kwargs):
    last_order = RentalOrder.objects.filter(item=instance).order_by('-id').first()
    if last_order:
        new_status = instance.status
        old_status = getattr(last_order, '_old_status', None)
        
        # لو الحالة اتغيرت
        if old_status != new_status:
            RentalOrder.objects.filter(pk=last_order.pk).update(status=new_status)
