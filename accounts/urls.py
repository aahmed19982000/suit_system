from django.urls import path
from . import views
from .views import mark_notification_as_read, delete_notification

urlpatterns = [
    path('', views.t_login, name='login'),
    path('login/', views.t_login, name='t_login'),
    path('signup/', views.signup_view, name='signup'),
    path('pos/employees-management/', views.employee_list, name='employee_list'),
    path('pos/employees/delete/<int:user_id>/', views.delete_employee, name='delete_employee'),

    path('logout/', views.logout_view, name='logout'), 
    path('no-permission/', views.no_permission, name='no_permission'),
    path('notifications/<int:notification_id>/read/', mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/<int:notification_id>/delete/', delete_notification, name='delete_notification'),

]
