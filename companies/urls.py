from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('', views.company_list, name='list'),
    path('<slug:slug>/', views.company_edit, name='edit'),
]
