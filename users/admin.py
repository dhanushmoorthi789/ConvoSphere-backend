from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'full_name', 'is_online', 'last_seen', 'is_active']
    list_filter = ['is_online', 'is_active', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']

    fieldsets = UserAdmin.fieldsets + (
        ('Chat Info', {'fields': ('phone', 'bio', 'avatar', 'is_online', 'last_seen', 'status_message')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra', {'fields': ('email', 'phone')}),
    )
