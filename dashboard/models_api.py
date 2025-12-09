"""
Модели для API токенов и управления балансом
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
import hashlib


class APIToken(models.Model):
    """API токен для доступа к сервису"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_tokens')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, help_text="Название токена для идентификации")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Статистика использования
    total_requests = models.IntegerField(default=0)
    total_generations = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'api_tokens'
        ordering = ['-created_at']
        verbose_name = 'API токен'
        verbose_name_plural = 'API токены'
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    @classmethod
    def generate_token(cls):
        """Генерация уникального токена"""
        return secrets.token_urlsafe(48)
    
    def get_masked_token(self):
        """Возвращает замаскированный токен для отображения"""
        if len(self.token) > 12:
            return f"{self.token[:8]}...{self.token[-4:]}"
        return self.token
    
    def mark_used(self):
        """Отметить использование токена"""
        self.last_used_at = timezone.now()
        self.total_requests += 1
        self.save(update_fields=['last_used_at', 'total_requests'])


class APIBalance(models.Model):
    """Баланс пользователя для API"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_balance')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Статистика
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deposited = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_balances'
        verbose_name = 'API баланс'
        verbose_name_plural = 'API балансы'
    
    def __str__(self):
        return f"{self.user.username} - ${self.balance}"
    
    def can_afford(self, amount):
        """Проверка достаточности средств"""
        return self.balance >= amount
    
    def charge(self, amount, description=""):
        """Списание средств"""
        if not self.can_afford(amount):
            raise ValueError("Недостаточно средств на балансе")
        
        self.balance -= amount
        self.total_spent += amount
        self.save()
        
        # Создаем запись транзакции
        APITransaction.objects.create(
            user=self.user,
            amount=-amount,
            transaction_type='charge',
            description=description,
            balance_after=self.balance
        )
    
    def deposit(self, amount, description=""):
        """Пополнение баланса"""
        self.balance += amount
        self.total_deposited += amount
        self.save()
        
        # Создаем запись транзакции
        APITransaction.objects.create(
            user=self.user,
            amount=amount,
            transaction_type='deposit',
            description=description,
            balance_after=self.balance
        )


class APITransaction(models.Model):
    """История транзакций API баланса"""
    
    TRANSACTION_TYPES = [
        ('deposit', 'Пополнение'),
        ('charge', 'Списание'),
        ('refund', 'Возврат'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_transactions'
        ordering = ['-created_at']
        verbose_name = 'API транзакция'
        verbose_name_plural = 'API транзакции'
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} ${self.amount}"


class APIUsageLog(models.Model):
    """Лог использования API"""
    
    token = models.ForeignKey(APIToken, on_delete=models.CASCADE, related_name='usage_logs')
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    
    # Детали запроса
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Результат
    status_code = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_usage_logs'
        ordering = ['-created_at']
        verbose_name = 'Лог использования API'
        verbose_name_plural = 'Логи использования API'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['token', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.token.name} - {self.endpoint} - {self.created_at}"
