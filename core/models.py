from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Add your custom fields and methods here
    pass

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

# Specify unique related_name attributes for groups and user_permissions fields
User._meta.get_field('groups').remote_field.related_name = 'core_user_groups'
User._meta.get_field('user_permissions').remote_field.related_name = 'core_user_permissions'
