from django.urls import path
from . import views


urlpatterns = [
    path('site/', views.site, name='site'),
    path('site/edit/<int:site_id>/', views.edit_site, name='edit_site'),
    path('delete/<int:site_id>/', views.delete_site , name='delete_site'),
    path('holiday/', views.holiday, name='holiday'),
    

    


]
