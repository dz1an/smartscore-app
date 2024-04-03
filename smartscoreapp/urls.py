from django.contrib import admin
from django.urls import path
from core import views as core_views  # Import the views from the core app
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.login_view, name='login'),  # Map the root URL to the login_view function
    path('index/', core_views.index, name='index'),
    # Add URL patterns for other views if needed
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

