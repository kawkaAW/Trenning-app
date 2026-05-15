from django import forms
from .models import BodyMetric, TrainingSession, UserPreference

class BodyMetricForm(forms.ModelForm):
    class Meta:
        model = BodyMetric
        fields = ['weight_kg', 'height_m', 'age', 'gender', 'fat_percentage', 'water_intake_liters', 'max_bpm', 'avg_bpm', 'resting_bpm']
        labels = {
            'weight_kg': 'Waga (kg)',
            'height_m': 'Wzrost (m)',
            'age': 'Wiek',
            'gender': 'Płeć',
            'fat_percentage': 'Procent tkanki tłuszczowej',
            'water_intake_liters': 'Spożycie wody (litry dziennie)',
            'max_bpm': 'Maksymalne tętno',
            'avg_bpm': 'średnie tętno',
            'resting_bpm': 'Tętno Spoczynkowe',
        }
        widgets = {
            'weight_kg': forms.NumberInput(attrs={'step': '0.1'}),
            'height_m': forms.NumberInput(attrs={'step': '0.01'}),
            'fat_percentage': forms.NumberInput(attrs={'step': '0.1'}),
            'water_intake_liters': forms.NumberInput(attrs={'step': '0.1'}),
        }
class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ['workout_frequency', 'experience_level', 'goal']

class TrainingSessionForm(forms.ModelForm):
    class Meta:
        model = TrainingSession
        fields = ['workout_type', 'session_duration', 'calories_burned']
        widgets = {
            'session_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CalendarTrainingForm(forms.ModelForm):
    class Meta:
        model = TrainingSession
        fields = ['workout_type', 'session_duration']
