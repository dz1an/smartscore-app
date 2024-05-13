from django.contrib import admin
from django.urls import path
from core import views as core_views  # Import the views from the core app
from django.conf.urls.static import static
from django.conf import settings
from .views import index, register_view, registered_users_view  # Import both index and register_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', register_view, name='register'),  # Add a URL pattern for the register view
    path('', core_views.login_view, name='login'),  # Map the root URL to the login_view function
    
    path('registered-users/', registered_users_view, name='registered_users'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
