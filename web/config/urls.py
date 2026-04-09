from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
    path('', RedirectView.as_view(url=f'/{settings.LANGUAGE_CODE}/', permanent=False)),
]

urlpatterns += i18n_patterns(
    path('', include('rates.urls')),
    prefix_default_language=True,
)
