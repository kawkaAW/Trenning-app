from django.contrib import admin
from .models import User, BodyMetric, TrainingSession, UserPreference

class TrainingSessionInline(admin.TabularInline):
    model = TrainingSession
    extra = 0  

class BodyMetricInline(admin.TabularInline):
    model = BodyMetric
    extra = 0

class UserPreferenceInline(admin.TabularInline):
    model = UserPreference
    extra = 0

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    inlines = [TrainingSessionInline, BodyMetricInline, UserPreferenceInline]

@admin.register(BodyMetric)
class BodyMetricAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight_kg', 'height_m', 'bmi', 'updated_at')
    search_fields = ('user__email',)

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'workout_frequency', 'experience_level', 'goal')
    search_fields = ('user__email',)

@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'workout_type', 'session_duration', 'session_date')  
    search_fields = ('user__email', 'workout_type')

