from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_staff', 'is_email_verified', 'created_at')
    search_fields = ('email', 'name')
    list_filter = ('is_staff', 'is_email_verified', 'is_active')
    readonly_fields = ('password',)