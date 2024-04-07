from django.contrib import admin
from django.urls import path
from core import views as core_views  # Import the views from the core app
from django.conf.urls.static import static
from django.conf import settings
from .views import index, register_view  # Import both index and register_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.login_view, name='login'),  # Map the root URL to the login_view function
    path('', index, name='index'),
    path('register/', register_view, name='register'),  # Add a URL pattern for the register view
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)