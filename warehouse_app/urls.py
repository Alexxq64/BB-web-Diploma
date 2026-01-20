from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # главная страница приложения
    path('nomenclature/', views.nomenclature_list, name='nomenclature_list'),
    path('nomenclature/add/', views.nomenclature_add, name='nomenclature_add'),    
    path('productbatch/', views.productbatch_list, name='productbatch_list'),
    path('operation/', views.operation_list, name='operation_list'),  
    path('warehouse/', views.warehouse_list, name='warehouse_list'),  
    path("productbatch/create/", views.productbatch_create, name="productbatch_create"),
    path("productbatch/<int:batch_id>/edit/", views.productbatch_create, name="productbatch_edit"),
    path("productbatch/receive/<int:batch_id>/", views.productbatch_receive, name="productbatch_receive"), 
    path('warehouse/deduction/<int:warehouse_id>/', views.warehouse_deduction, name='warehouse_deduction'),   
    path('export/', views.export_data, name='export_page'),      
]
