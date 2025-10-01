from django.contrib import admin
from .models import Wallet

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "purchased_total", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")

