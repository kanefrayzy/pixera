"""
URL маршруты для API управления
"""
from django.urls import path
from . import views_api
from . import notifications_views as notif

app_name = 'api'

urlpatterns = [
    # Главная страница API
    path('', views_api.api_dashboard, name='dashboard'),

    # Admin top-up (staff only)
    path('admin/topup/', views_api.admin_topup, name='admin_topup'),

    # Управление токенами
    path('tokens/create/', views_api.create_token, name='create_token'),
    path('tokens/<int:token_id>/delete/', views_api.delete_token, name='delete_token'),
    path('tokens/<int:token_id>/toggle/', views_api.toggle_token, name='toggle_token'),

    # Документация
    path('documentation/', views_api.api_documentation, name='documentation'),

    # Баланс
    path('balance/', views_api.api_balance_page, name='balance'),
    path('balance/deposit/', views_api.deposit_balance, name='deposit_balance'),

    # Статистика
    path('stats/', views_api.api_usage_stats, name='usage_stats'),

    # API endpoint для проверки баланса
    path('check-balance/', views_api.check_balance_api, name='check_balance_api'),
    # Wallet info for drawer live-refresh
    path('wallet/info/', views_api.wallet_info, name='wallet_info'),

    # Подписки
    path('follow/toggle/', views_api.follow_toggle, name='follow_toggle'),
    path('follow/<str:username>/counters/', views_api.follow_counters, name='follow_counters'),
    path('follow/search/', views_api.follow_search, name='follow_search'),
    path('follow/recommendations/', views_api.follow_recommendations, name='follow_recommendations'),
    path('follow/list/followers/', views_api.follow_list_followers, name='follow_list_followers'),
    path('follow/list/following/', views_api.follow_list_following, name='follow_list_following'),

    # Jobs: hide/unhide in profile
    path('jobs/<int:job_id>/toggle-hidden/', views_api.job_toggle_hidden, name='job_toggle_hidden'),

    # Notifications
    path('notifications/list/', notif.notifications_list, name='notifications_list'),
    path('notifications/unread-count/', notif.notifications_unread_count, name='notifications_unread_count'),
    path('notifications/mark-read/', notif.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/mark-all-read/', notif.notifications_mark_all_read, name='notifications_mark_all_read'),

    # Account settings (self-service)
    path('account/change-email/', views_api.account_change_email, name='account_change_email'),
    path('account/change-username/', views_api.account_change_username, name='account_change_username'),

    # Profile: mixed published feed (photos + videos)
    path('profile/published/', views_api.profile_published_feed, name='profile_published_feed'),
]
