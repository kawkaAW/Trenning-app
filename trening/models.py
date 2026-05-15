from datetime import date
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Tworzy i zwraca użytkownika z podanym adresem email i hasłem.
        """
        if not email:
            raise ValueError("Adres email jest wymagany")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Tworzy i zwraca superużytkownika.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError("Superuser musi mieć is_staff=True.")
        if not extra_fields.get('is_superuser'):
            raise ValueError("Superuser musi mieć is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')], blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class DailyPlan(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    date = models.DateField()
    has_training = models.BooleanField(default=False)
    training_type = models.CharField(max_length=50, blank=True, null=True)  
    calorie_balance = models.FloatField(default=0.0)
    hydration_level = models.FloatField(default=0.0) 

class TrainingPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

class TrainingPlanEntry(models.Model):
    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name="entries")
    day_of_week = models.CharField(
        max_length=10,
        choices=[
            ('Monday', 'Poniedziałek'),
            ('Tuesday', 'Wtorek'),
            ('Wednesday', 'Środa'),
            ('Thursday', 'Czwartek'),
            ('Friday', 'Piątek'),
            ('Saturday', 'Sobota'),
            ('Sunday', 'Niedziela'),
        ],
    )
    workout_type = models.CharField(max_length=50, help_text="Typ treningu (np. Cardio, Siłowy)")
    duration_minutes = models.IntegerField(help_text="Czas trwania treningu w minutach")
    description = models.TextField(blank=True, help_text="Szczegóły dotyczące treningu")

    def __str__(self):
        return f"{self.day_of_week}: {self.workout_type} ({self.duration_minutes} min)"

def default_session_date():
    return date.today().isoformat()


class TrainingSession(models.Model):
    session_date = models.DateField(default=date.today, help_text="Data treningu")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='training_sessions')
    workout_type = models.CharField(max_length=50, help_text="Rodzaj treningu")
    session_duration = models.FloatField(help_text="Czas trwania treningu w godzinach")
    max_bpm = models.IntegerField(help_text="Maksymalne tętno podczas sesji", blank=True, null=True)
    avg_bpm = models.IntegerField(help_text="Średnie tętno podczas sesji", blank=True, null=True)
    resting_bpm = models.IntegerField(help_text="Spoczynkowe tętno", blank=True, null=True)
    calories_burned = models.IntegerField(help_text="Ilość spalonych kalorii", blank=True, null=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Training on {self.session_date} for {self.user.email}"

class TrainingReport(models.Model):
    training = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name="reports"
    )
    actual_duration = models.FloatField()  
    actual_calories = models.FloatField()  
    actual_avg_bpm = models.IntegerField()  
    actual_max_bpm = models.IntegerField()  
    comments = models.TextField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Raport: {self.training.workout_type} ({self.training.session_date})"


class BodyMetric(models.Model):
    """
    Przechowuje dane biometryczne użytkownika.
    """
    GENDER_CHOICES = [
        ('M', 'Mężczyzna'),
        ('F', 'Kobieta'),
        ('O', 'Inna'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='body_metric')
    weight_kg = models.FloatField(help_text="Waga w kilogramach")
    height_m = models.FloatField(help_text="Wzrost w metrach")
    age = models.IntegerField(help_text="Wiek użytkownika", blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, help_text="Płeć użytkownika", blank=True, null=True)
    bmi = models.FloatField(blank=True, null=True, help_text="BMI (obliczane automatycznie)")
    fat_percentage = models.FloatField(blank=True, null=True, help_text="Procent tkanki tłuszczowej")
    water_intake_liters = models.FloatField(help_text="Spożycie wody w litrach dziennie")
    max_bpm = models.IntegerField(blank=True, null=True, help_text="Maksymalne tętno podczas treningu")
    avg_bpm = models.IntegerField(blank=True, null=True, help_text="Średnie tętno podczas treningu")
    resting_bpm = models.IntegerField(blank=True, null=True, help_text="Tętno spoczynkowe")
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.height_m and self.weight_kg:  
            try:
                height = float(self.height_m)
                weight = float(self.weight_kg)
                if height > 0: 
                    self.bmi = weight / (height ** 2)
            except ValueError:
                raise ValueError("Height and weight must be numbers.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Body metrics for {self.user.email}"

class UserPreference(models.Model):
    """
    Przechowuje preferencje treningowe użytkownika.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    workout_frequency = models.IntegerField(choices=[
        (1, '1-2 razy w tygodniu'),
        (2, '3-4 razy w tygodniu'),
        (3, '5-7 razy w tygodniu')
    ], help_text="Częstotliwość treningów")
    experience_level = models.IntegerField(choices=[
        (1, 'Początkujący'),
        (2, 'Średniozaawansowany'),
        (3, 'Zaawansowany')
    ], help_text="Poziom doświadczenia")
    goal = models.TextField(blank=True, null=True, help_text="Cel treningowy")

    def __str__(self):
        return f"Preferences for {self.user.email}"

class ExerciseHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exercise_title = models.CharField(max_length=255)
    date = models.DateField()

    def __str__(self):
        return f"{self.user.email} - {self.exercise_title} - {self.date}"

class DailyUserStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField(auto_now_add=True)
    weight = models.FloatField(null=True, blank=True, help_text="Waga w kilogramach")
    calorie_balance = models.IntegerField(null=True, blank=True, help_text="Bilans kaloryczny")
    calories_consumed = models.IntegerField(null=True, blank=True, help_text="Kalorie spożyte")
    hydration = models.FloatField(null=True, blank=True, help_text="Nawodnienie w litrach")

    def calculate_calorie_balance(self):
        total_calories_burned = sum(
            report.actual_calories
            for training in self.user.training_sessions.filter(session_date=self.date)
            for report in training.reports.all()
        )
        return (self.calories_consumed or 0) - total_calories_burned

    def save(self, *args, **kwargs):
        self.calorie_balance = self.calculate_calorie_balance()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Statystyki dla {self.user.email} - {self.date}"
    
class TrainingGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="training_goals")
    goal_type = models.CharField(max_length=255, choices=[
        ('weight_loss', 'Zrzucenie wagi'),
        ('muscle_gain', 'Budowa masy mięśniowej'),
        ('endurance', 'Wytrzymałość'),
        ('training_completion', 'Ukończenie treningów'),
        ('calories_burned', 'Spalenie kalorii'),  
    ])
    target_value = models.FloatField(help_text="Docelowa wartość (np. waga w kg, liczba godzin treningu, % ukończonych treningów, kalorie)")
    current_progress = models.FloatField(default=0.0, help_text="Postęp użytkownika")
    deadline = models.DateField()
    is_completed = models.BooleanField(default=False)

    def update_progress(self):
        """Aktualizuj postęp celu na podstawie jego typu."""
        if self.goal_type == 'training_completion':
            total_trainings = TrainingSession.objects.filter(user=self.user, session_date__lte=self.deadline).count()
            completed_trainings = TrainingSession.objects.filter(user=self.user, completed=True, session_date__lte=self.deadline).count()
            self.current_progress = (completed_trainings / total_trainings) * 100 if total_trainings > 0 else 0
        
        elif self.goal_type == 'weight_loss':
            last_daily_stats = DailyUserStats.objects.filter(user=self.user).order_by('-date').first()
            if last_daily_stats and last_daily_stats.weight is not None:
                self.current_progress = last_daily_stats.weight
            if self.current_progress <= self.target_value:  
                self.is_completed = True
        
        elif self.goal_type == 'muscle_gain':
            last_daily_stats = DailyUserStats.objects.filter(user=self.user).order_by('-date').first()
            if last_daily_stats and last_daily_stats.weight is not None:
                self.current_progress = last_daily_stats.weight
            if self.current_progress >= self.target_value:  
                self.is_completed = True
        
        elif self.goal_type == 'calories_burned':
            from django.db.models import Sum
            total_calories = TrainingReport.objects.filter(training__user=self.user).aggregate(Sum('actual_calories'))['actual_calories__sum'] or 0
            self.current_progress = total_calories
            if self.current_progress >= self.target_value:  
                self.is_completed = True

        self.save()

    def __str__(self):
        return f"Cel: {self.get_goal_type_display()} dla {self.user.email}"



class Reward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rewards")
    description = models.CharField(max_length=255)
    points_required = models.IntegerField()
    is_redeemed = models.BooleanField(default=False)

    @staticmethod
    def assign_for_training_completion(user):
        """Przyznaj nagrodę za osiągnięcie celu treningowego."""
        completed_goals = TrainingGoal.objects.filter(user=user, goal_type='training_completion', is_completed=True)
        assigned_rewards = []  

        for goal in completed_goals:
            reward, created = Reward.objects.get_or_create(
                user=user,
                description=f"Nagroda za ukończenie {goal.target_value}% treningów",
                points_required=100,
            )
            if created:  
                assigned_rewards.append(reward)

        return assigned_rewards  
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Powiadomienie dla {self.user.email}: {self.message[:50]}{'...' if len(self.message) > 50 else ''}"
