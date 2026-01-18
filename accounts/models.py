
# models.py
from django.contrib.auth.models import User , AbstractUser
from django.db import models
from django.conf import settings


class Users(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'مدير'),
        ('employee', 'موظف'),
        ('designer', 'Designer'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    job_title = models.CharField(max_length=100, blank=True, null=True)
    mobile = models.CharField(max_length=15)

    def __str__(self):
        return self.get_full_name() or self.username


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    link = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


    def __str__(self):

        return f"To: {self.user.username} - {self.message[:30]}"
