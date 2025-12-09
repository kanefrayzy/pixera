"""
URL patterns for video content management API
"""
from django.urls import path
from . import views_video_content_api as views

app_name = 'video_content'

urlpatterns = [
    # Video Prompt Categories
    path('api/video/categories/', views.list_video_categories, name='list_categories'),
    path('api/video/categories/create/', views.create_video_category, name='create_category'),
    path('api/video/categories/<int:category_id>/update/', views.update_video_category, name='update_category'),
    path('api/video/categories/<int:category_id>/delete/', views.delete_video_category, name='delete_category'),
    path('api/video/categories/<int:category_id>/prompts', views.get_category_prompts, name='category_prompts'),

    # Video Prompt Subcategories
    path('api/video/categories/<int:category_id>/subcategories', views.video_category_subcategories_api, name='video_pc_subcategories'),
    path('api/video/subcategories/create', views.create_video_subcategory, name='video_sc_create'),
    path('api/video/subcategories/<int:subcategory_id>/update', views.update_video_subcategory, name='video_sc_update'),
    path('api/video/subcategories/<int:subcategory_id>/delete', views.delete_video_subcategory, name='video_sc_delete'),
    path('api/video/subcategories/<int:subcategory_id>/prompts', views.video_subcategory_prompts_api, name='video_sc_prompts'),

    # Video Prompts
    path('api/video/prompts/', views.list_video_prompts, name='list_prompts'),
    path('api/video/prompts/create/', views.create_video_prompt, name='create_prompt'),
    path('api/video/prompts/<int:prompt_id>/update/', views.update_video_prompt, name='update_prompt'),
    path('api/video/prompts/<int:prompt_id>/delete/', views.delete_video_prompt, name='delete_prompt'),

    # Video Showcase
    path('api/video/showcase/', views.list_video_showcase, name='list_showcase'),
    path('api/video/showcase/create/', views.create_video_showcase, name='create_showcase'),
    path('api/video/showcase/<int:video_id>/update/', views.update_video_showcase, name='update_showcase'),
    path('api/video/showcase/<int:video_id>/delete/', views.delete_video_showcase, name='delete_showcase'),
]
