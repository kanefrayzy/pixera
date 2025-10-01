# dashboard/models.py
from django.db import models
from django.conf import settings

STARTER_TOKENS = 0  # новый кошелёк = 0, чтобы «три гостевые обработки» не возвращались после входа

class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance = models.PositiveIntegerField(default=STARTER_TOKENS)  # токены на руках
    purchased_total = models.PositiveIntegerField(default=0)       # всего куплено
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def charge(self, amount: int) -> bool:
        if amount <= 0:
            return True
        if self.balance < amount:
            return False
        self.balance -= amount
        self.save(update_fields=["balance", "updated_at"])
        return True

    def topup(self, amount: int):
        if amount <= 0:
            return
        self.balance += amount
        self.purchased_total += amount
        self.save(update_fields=["balance", "purchased_total", "updated_at"])

    def __str__(self):
        return f"Wallet({self.user_id}) = {self.balance}"
