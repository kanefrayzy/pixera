from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generate', '0010_seed_large_suggestions'),
    ]

    operations = [
        # Создаём новую модель для категорий подсказок с изображениями
        migrations.CreateModel(
            name='PromptCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='Слаг')),
                ('description', models.TextField(blank=True, default='', verbose_name='Описание')),
                ('image', models.ImageField(upload_to='prompt_categories/', verbose_name='Изображение категории')),
                ('order', models.PositiveIntegerField(default=0, db_index=True, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, db_index=True, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Категория промптов',
                'verbose_name_plural': 'Категории промптов',
                'ordering': ('order', 'name'),
            },
        ),
        
        # Создаём модель для промптов внутри категорий
        migrations.CreateModel(
            name='CategoryPrompt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150, verbose_name='Заголовок')),
                ('prompt_text', models.TextField(verbose_name='Текст промпта')),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='prompts',
                    to='generate.promptcategory',
                    verbose_name='Категория'
                )),
                ('order', models.PositiveIntegerField(default=0, db_index=True, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, db_index=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Промпт категории',
                'verbose_name_plural': 'Промпты категорий',
                'ordering': ('order', 'title'),
            },
        ),
        
        # Добавляем индексы
        migrations.AddIndex(
            model_name='promptcategory',
            index=models.Index(fields=['is_active', 'order'], name='gen_pcat_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='categoryprompt',
            index=models.Index(fields=['category', 'is_active', 'order'], name='gen_cprompt_cat_active_idx'),
        ),
    ]
