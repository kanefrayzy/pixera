import os
import json
import subprocess
from django.db import models
from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image


class VideoSliderExample(models.Model):
    """Модель видео-примеров для слайдера на главной (аналог SliderExample, но с видео)."""

    json_id = models.IntegerField(help_text="ID в JSON файле", blank=True, null=True, db_index=True)
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    prompt = models.TextField(verbose_name="Промт")

    # Видео: ссылка (например, на mp4) и опциональный постер
    video_url = models.URLField(max_length=500, verbose_name="URL видео", blank=True, default="")
    thumbnail = models.ImageField(
        upload_to="slider_video_examples/",
        verbose_name="Постер (превью)",
        help_text="Опционально: изображение-постер для видео",
        blank=True,
        null=True,
    )
    # Загружаемый видеофайл (будет сжат ffmpeg и сохранён как MP4 с faststart)
    video_file = models.FileField(
        upload_to="slider_video_examples/%Y/%m/",
        verbose_name="Видео файл",
        blank=True,
        null=True,
    )

    description = models.CharField(max_length=500, verbose_name="Описание", blank=True, default="")
    # Настройки генерации
    steps = models.IntegerField(default=28, verbose_name="Количество шагов")
    cfg = models.FloatField(default=7.0, verbose_name="CFG Scale")
    seed = models.CharField(
        max_length=20,
        default="auto",
        verbose_name="Seed",
        help_text="Введите число или 'auto' для случайного",
    )

    order = models.PositiveIntegerField(default=0, verbose_name="Порядок отображения", db_index=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Видео-пример слайдера"
        verbose_name_plural = "Видео-примеры слайдера"
        ordering = ["order", "json_id"]
        indexes = [
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self):
        return f"{self.title} (VID: {self.json_id})"

    @property
    def ratio(self):
        """Соотношение сторон (визуально используем такое же, как у изображений в демо)"""
        return "3:2"

    @property
    def video_src(self) -> str:
        """URL видео-источника: приоритет у загруженного файла, иначе URL."""
        try:
            if self.video_file and getattr(self.video_file, "url", None):
                return self.video_file.url
        except Exception:
            pass
        return getattr(self, "video_url", "") or ""

    @classmethod
    def get_json_file_path(cls):
        """Путь к JSON файлу данных видеослайдера."""
        return os.path.join(settings.BASE_DIR, "static", "data", "slider_video_examples.json")

    @classmethod
    def load_from_json(cls):
        """Импортировать данные из JSON файла в БД (обновляет/создаёт по json_id)."""
        json_path = cls.get_json_file_path()
        if not os.path.exists(json_path):
            return False, "JSON файл для видео не найден"

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                cls.objects.update_or_create(
                    json_id=item.get("id"),
                    defaults={
                        "title": item.get("title") or "",
                        "prompt": item.get("prompt") or "",
                        "video_url": item.get("video") or "",
                        "description": item.get("description") or "",
                        "steps": int(item.get("settings", {}).get("steps", 28) or 28),
                        "cfg": float(item.get("settings", {}).get("cfg", 7.0) or 7.0),
                        "seed": str(item.get("settings", {}).get("seed", "auto") or "auto"),
                        "order": int(item.get("order", item.get("id", 0)) or 0),
                    },
                )
            return True, f"Загружено {len(data)} видео-записей"
        except Exception as e:
            return False, f"Ошибка при загрузке видео JSON: {str(e)}"

    @classmethod
    def export_to_json(cls):
        """Экспорт активных записей в JSON файл (для фронтенда слайдера на главной)."""
        json_path = cls.get_json_file_path()
        try:
            videos = cls.objects.filter(is_active=True).order_by("order", "json_id")
            data = []
            for v in videos:
                thumb_url = v.thumbnail.url if v.thumbnail else ""
                data.append(
                    {
                        "id": v.json_id,
                        "title": v.title,
                        "prompt": v.prompt,
                        "video": v.video_src,
                        "thumbnail": thumb_url,
                        "description": v.description,
                        "settings": {
                            "steps": v.steps,
                            "cfg": v.cfg,
                            "ratio": v.ratio,
                            "seed": v.seed if v.seed != "auto" else "auto",
                        },
                        "order": v.order,
                    }
                )

            # Резервная копия
            if os.path.exists(json_path):
                import shutil

                shutil.copy2(json_path, json_path + ".bak")

            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True, f"Экспортировано {len(data)} видео-записей"
        except Exception as e:
            return False, f"Ошибка при экспорте видео JSON: {str(e)}"

    def save(self, *args, **kwargs):
        # Автоприсвоение json_id
        if not self.json_id:
            max_id = VideoSliderExample.objects.aggregate(models.Max("json_id"))["json_id__max"]
            self.json_id = (max_id or -1) + 1

        super().save(*args, **kwargs)

        # Попытаться сжать видео (если загружено и ещё не сжато)
        try:
            self._maybe_compress_video()
        except Exception:
            # Без падения транзакции — в лог можно добавить при необходимости
            pass

        # Попытаться сжать превью-изображение (thumbnail)
        try:
            self._maybe_compress_thumbnail()
        except Exception:
            pass

        # Экспортируем JSON (можно отключить через skip_export=True)
        if not kwargs.get("skip_export", False):
            VideoSliderExample.export_to_json()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if not kwargs.get("skip_export", False):
            VideoSliderExample.export_to_json()

    # --- helpers --------------------------------------------------------------
    def _maybe_compress_video(self) -> None:
        """Сжимает загруженное видео до MP4 (H.264, faststart) с сильной компрессией.
        Запускается после save(). Безопасно завершится, если ffmpeg недоступен."""
        file_field = getattr(self, "video_file", None)
        name = getattr(file_field, "name", "") or ""
        if not name:
            return
        # Пропускаем, если уже сжатое (по суффиксу)
        if name.lower().endswith("_cmp.mp4"):
            return

        # Локальный путь к исходнику
        try:
            in_path = default_storage.path(name)
        except Exception:
            return
        if not in_path or not os.path.exists(in_path):
            return

        base, _ = os.path.splitext(in_path)
        out_path = base + "_cmp.mp4"

        ffmpeg = getattr(settings, "FFMPEG_BIN", "ffmpeg")
        # Максимальная компрессия при приемлемом качестве для предпросмотра:
        # - CRF 32 (можно 33-35 для ещё меньшего размера), preset veryslow,
        # - ограничение ширины до 1280px, fps=24, faststart для прогрессивной загрузки
        cmd = [
            ffmpeg,
            "-y",
            "-i", in_path,
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            "-vcodec", "libx264",
            "-preset", "veryslow",
            "-crf", "36",
            "-vf", "scale='min(720,iw)':'-2',fps=20",
            "-acodec", "aac",
            "-ac", "1",
            "-b:a", "48k",
            out_path,
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc.returncode != 0 or not os.path.exists(out_path):
                return
            # Заменяем файл в FileField на сжатый вариант
            media_root = getattr(settings, "MEDIA_ROOT", "")
            rel = os.path.relpath(out_path, media_root) if media_root and os.path.isabs(out_path) else out_path
            rel = rel.replace("\\", "/")
            if rel != name:
                # Обновляем путь и сохраняем только поле
                self.video_file.name = rel
                super(VideoSliderExample, self).save(update_fields=["video_file"])
                # Удаляем исходник
                try:
                    if os.path.exists(in_path):
                        os.remove(in_path)
                except Exception:
                    pass
        except Exception:
            # Тихо игнорируем ошибки кодека
            return

    def _maybe_compress_thumbnail(self) -> None:
        """Сжимает thumbnail (ImageField) до webp с ограничением ширины 960px."""
        thumb_field = getattr(self, "thumbnail", None)
        name = getattr(thumb_field, "name", "") or ""
        if not name:
            return
        try:
            in_path = default_storage.path(name)
        except Exception:
            in_path = None
        if not in_path or not os.path.exists(in_path):
            return

        base, _ = os.path.splitext(in_path)
        out_path = base + "_cmp.webp"
        try:
            from PIL import Image as PILImage  # safety import
            with PILImage.open(in_path) as im:
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                w, h = im.size
                max_w = 960
                if w > max_w:
                    new_h = int(h * (max_w / float(w)))
                    im = im.resize((max_w, new_h), PILImage.LANCZOS)
                im.save(out_path, "WEBP", quality=70, method=6, optimize=True)

            media_root = getattr(settings, "MEDIA_ROOT", "")
            rel = os.path.relpath(out_path, media_root) if media_root and os.path.isabs(out_path) else out_path
            rel = rel.replace("\\", "/")
            if rel and rel != name:
                self.thumbnail.name = rel
                super(VideoSliderExample, self).save(update_fields=["thumbnail"])
                try:
                    if os.path.exists(in_path):
                        os.remove(in_path)
                except Exception:
                    pass
        except Exception:
            return
