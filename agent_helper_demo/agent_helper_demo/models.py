from django.conf import settings
from django.db import models


class DemoNote(models.Model):
    """یادداشت کاربر (افزونه‌ی نمونه)"""
    class Meta:
        verbose_name = 'یادداشت نمونه'
        verbose_name_plural = 'یادداشت‌های نمونه'
        ordering = ['-id']

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='demo_notes', verbose_name='کاربر')
    text = models.CharField(max_length=500, verbose_name='متن')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')

    def __str__(self):
        return self.text[:40]
