from django.urls import path
from . import views_slider

app_name = 'slider'

urlpatterns = [
    # Список примеров
    path('', views_slider.slider_examples_list, name='list'),

    # CRUD операции
    path('create/', views_slider.slider_example_create, name='create'),
    path('<int:pk>/edit/', views_slider.slider_example_edit, name='edit'),
    path('<int:pk>/delete/', views_slider.slider_example_delete, name='delete'),
    path('<int:pk>/preview/', views_slider.slider_example_preview, name='preview'),

    # Массовые операции
    path('import/', views_slider.slider_examples_import, name='import'),
    path('export/', views_slider.slider_examples_export, name='export'),

    # AJAX операции
    path('<int:pk>/toggle-active/', views_slider.slider_example_toggle_active, name='toggle_active'),
    path('reorder/', views_slider.slider_examples_reorder, name='reorder'),
]
