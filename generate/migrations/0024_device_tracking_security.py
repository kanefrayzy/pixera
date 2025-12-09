# Generated migration for device tracking security

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0026_videopromptsubcategory_videoprompt_subcategory_and_more'),
    ]

    operations = [
        # Таблица для отслеживания устройств с жёсткой привязкой
        migrations.CreateModel(
            name='DeviceFingerprint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),

                # Уровень 1: Жёсткий отпечаток браузера (fp)
                ('fp', models.CharField(max_length=64, unique=True, db_index=True, help_text='Жёсткий отпечаток браузера')),

                # Уровень 2: Cookie GID (стойкий идентификатор)
                ('gid', models.CharField(max_length=64, db_index=True, help_text='Стойкий cookie идентификатор')),

                # Уровень 3: IP hash (защита от VPN)
                ('ip_hash', models.CharField(max_length=64, db_index=True, help_text='Хеш IP адреса')),

                # Уровень 4: UA hash (отпечаток браузера)
                ('ua_hash', models.CharField(max_length=64, db_index=True, help_text='Хеш User-Agent')),

                # Дополнительные данные для анализа
                ('first_ip', models.GenericIPAddressField(null=True, blank=True, help_text='Первый IP адрес')),
                ('session_keys', models.JSONField(default=list, help_text='История session keys')),

                # Флаги безопасности
                ('is_vpn_detected', models.BooleanField(default=False, db_index=True, help_text='Обнаружен VPN')),
                ('is_incognito_detected', models.BooleanField(default=False, db_index=True, help_text='Обнаружен инкогнито')),
                ('is_blocked', models.BooleanField(default=False, db_index=True, help_text='Заблокирован за попытки обхода')),

                # Счётчики попыток обхода
                ('bypass_attempts', models.PositiveIntegerField(default=0, help_text='Попытки обхода системы')),
                ('last_bypass_attempt', models.DateTimeField(null=True, blank=True)),

                # Связь с FreeGrant (один к одному)
                ('free_grant', models.OneToOneField(
                    'FreeGrant',
                    on_delete=models.CASCADE,
                    related_name='device_fingerprint',
                    null=True,
                    blank=True,
                    help_text='Связанный грант'
                )),
            ],
            options={
                'verbose_name': 'Отпечаток устройства',
                'verbose_name_plural': 'Отпечатки устройств',
                'indexes': [
                    models.Index(fields=['fp', 'is_blocked'], name='device_fp_blocked_idx'),
                    models.Index(fields=['gid', 'is_blocked'], name='device_gid_blocked_idx'),
                    models.Index(fields=['ip_hash', 'is_blocked'], name='device_ip_blocked_idx'),
                    models.Index(fields=['ua_hash', 'is_blocked'], name='device_ua_blocked_idx'),
                    models.Index(fields=['is_blocked', 'created_at'], name='device_blocked_created_idx'),
                ],
            },
        ),

        # Таблица для логирования попыток получения токенов
        migrations.CreateModel(
            name='TokenGrantAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),

                # Идентификаторы попытки
                ('fp', models.CharField(max_length=64, db_index=True)),
                ('gid', models.CharField(max_length=64, db_index=True)),
                ('ip_hash', models.CharField(max_length=64, db_index=True)),
                ('ua_hash', models.CharField(max_length=64, db_index=True)),
                ('session_key', models.CharField(max_length=64, blank=True, default='')),

                # IP адрес
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),

                # Результат попытки
                ('was_granted', models.BooleanField(default=False, help_text='Были ли выданы токены')),
                ('was_blocked', models.BooleanField(default=False, help_text='Была ли попытка заблокирована')),
                ('block_reason', models.CharField(max_length=200, blank=True, default='', help_text='Причина блокировки')),

                # Связь с устройством
                ('device', models.ForeignKey(
                    'DeviceFingerprint',
                    on_delete=models.SET_NULL,
                    null=True,
                    blank=True,
                    related_name='grant_attempts'
                )),
            ],
            options={
                'verbose_name': 'Попытка получения токенов',
                'verbose_name_plural': 'Попытки получения токенов',
                'indexes': [
                    models.Index(fields=['fp', 'created_at'], name='attempt_fp_created_idx'),
                    models.Index(fields=['gid', 'created_at'], name='attempt_gid_created_idx'),
                    models.Index(fields=['ip_hash', 'created_at'], name='attempt_ip_created_idx'),
                    models.Index(fields=['was_blocked', 'created_at'], name='attempt_blocked_created_idx'),
                ],
            },
        ),
    ]
