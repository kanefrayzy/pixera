from django.contrib import admin
from .models import Wallet
from .models_api import APIToken, APIBalance, APITransaction, APIUsageLog


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'purchased_total', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_active', 'total_requests', 'total_generations', 'created_at', 'last_used_at')
    list_filter = ('is_active', 'created_at', 'last_used_at')
    search_fields = ('name', 'user__username', 'user__email', 'token')
    readonly_fields = ('token', 'created_at', 'last_used_at', 'total_requests', 'total_generations')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'name', 'token', 'is_active')
        }),
        ('Статистика', {
            'fields': ('total_requests', 'total_generations', 'created_at', 'last_used_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields


@admin.register(APIBalance)
class APIBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'total_spent', 'total_deposited', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'total_spent', 'total_deposited')
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Баланс', {
            'fields': ('balance',)
        }),
        ('Статистика', {
            'fields': ('total_spent', 'total_deposited', 'created_at', 'updated_at')
        }),
    )


@admin.register(APITransaction)
class APITransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Транзакция', {
            'fields': ('user', 'transaction_type', 'amount', 'balance_after')
        }),
        ('Детали', {
            'fields': ('description', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        # Транзакции создаются только программно
        return False
    
    def has_change_permission(self, request, obj=None):
        # Транзакции нельзя изменять
        return False


@admin.register(APIUsageLog)
class APIUsageLogAdmin(admin.ModelAdmin):
    list_display = ('token', 'endpoint', 'method', 'status_code', 'cost', 'ip_address', 'created_at')
    list_filter = ('method', 'status_code', 'created_at')
    search_fields = ('token__name', 'token__user__username', 'endpoint', 'ip_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Запрос', {
            'fields': ('token', 'endpoint', 'method', 'status_code')
        }),
        ('Детали', {
            'fields': ('ip_address', 'user_agent', 'cost', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        # Логи создаются только программно
        return False
    
    def has_change_permission(self, request, obj=None):
        # Логи нельзя изменять
        return False
