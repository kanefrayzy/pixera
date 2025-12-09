from django.urls import path
from . import views_slider

app_name = 'slider'

urlpatterns = [
    # Список примеров
    path('', views_slider.slider_examples_list, name='list'),

    # CRUD операции (фото)
    path('create/', views_slider.slider_example_create, name='create'),
    path('<int:pk>/edit/', views_slider.slider_example_edit, name='edit'),
    path('<int:pk>/delete/', views_slider.slider_example_delete, name='delete'),
    path('<int:pk>/preview/', views_slider.slider_example_preview, name='preview'),

    # Массовые операции (фото)
    path('import/', views_slider.slider_examples_import, name='import'),
    path('export/', views_slider.slider_examples_export, name='export'),

    # AJAX операции (фото)
    path('<int:pk>/toggle-active/', views_slider.slider_example_toggle_active, name='toggle_active'),
    path('reorder/', views_slider.slider_examples_reorder, name='reorder'),

    # CRUD операции (видео)
    path('videos/create/', views_slider.video_slider_example_create, name='video_create'),
    path('videos/<int:pk>/edit/', views_slider.video_slider_example_edit, name='video_edit'),
    path('videos/<int:pk>/delete/', views_slider.video_slider_example_delete, name='video_delete'),
    path('videos/<int:pk>/preview/', views_slider.video_slider_example_preview, name='video_preview'),

    # AJAX операции (видео)
    path('videos/<int:pk>/toggle-active/', views_slider.video_slider_example_toggle_active, name='video_toggle_active'),
    path('videos/reorder/', views_slider.video_slider_examples_reorder, name='video_reorder'),
]
