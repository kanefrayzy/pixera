from django import template
from dashboard.models import Follow

register = template.Library()


@register.filter
def is_following(user, target_user):
    """
    Проверяет подписан ли user на target_user.
    Использование: {% if request.user|is_following:comment_author %}
    """
    if not user or not target_user:
        return False
    if not user.is_authenticated:
        return False
    if user.id == target_user.id:
        return False  # Нельзя подписаться на самого себя

    return Follow.objects.filter(follower=user, following=target_user).exists()
