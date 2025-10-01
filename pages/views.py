# pages/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

def age_accept(request):
    resp = JsonResponse({"ok": True})
    # ставим куку на 365 дней
    resp.set_cookie("age_ok", "1", max_age=60*60*24*365, samesite="Lax", secure=False, path="/")
    return resp

def home(request):
    # Получаем трендовые фотографии для главной страницы
    trending_photos = get_trending_photos()
    
    context = {
        'trending_photos': trending_photos,
    }
    return render(request, "pages/home.html", context)

def get_trending_photos():

    try:
        from gallery.models import PublicPhoto
        
        # Получаем фото за последний месяц
        last_month = timezone.now() - timedelta(days=30)
        
        trending_by_likes = PublicPhoto.objects.filter(
            created_at__gte=last_month,
            is_active=True
        ).select_related('uploaded_by').order_by('-likes_count', '-view_count')[:12]
        return trending_by_likes
        
    except ImportError:
        # Если модель PublicPhoto не существует или приложение gallery не подключено
        return []
    except Exception as e:
        # Логируем ошибку, но не ломаем страницу
        print(f"Error getting trending photos: {e}")
        return []

class RobotsView(TemplateView):
    template_name = "pages/robots.txt"
    content_type = "text/plain"

def about(request):
    return render(request, "pages/about.html")

def contact(request):
    return render(request, "pages/contact.html")

def privacy(request):
    return render(request, "pages/privacy.html")