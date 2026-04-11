from django.db import models


class TelegramMiniAppUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    language_code = models.CharField(max_length=16, blank=True)
    photo_url = models.URLField(blank=True)
    is_premium = models.BooleanField(default=False)
    allows_write_to_pm = models.BooleanField(default=False)
    last_auth_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Telegram Mini App user"
        verbose_name_plural = "Telegram Mini App users"

    def __str__(self) -> str:
        display_name = " ".join(part for part in [self.first_name, self.last_name] if part).strip()
        return display_name or self.username or str(self.telegram_id)
