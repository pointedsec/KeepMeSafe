from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class AdminProfile(admin.ModelAdmin):
    last_display = ('name', 'created_at', 'updated_at')