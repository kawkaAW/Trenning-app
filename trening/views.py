from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from .models import DailyPlan, Notification, Reward, TrainingGoal
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import TrainingPlan
from .forms import BodyMetricForm, TrainingSessionForm, UserPreferenceForm
from .models import BodyMetric, TrainingSession, UserPreference, TrainingReport, ExerciseHistory, DailyUserStats
from .forms import CalendarTrainingForm
import calendar
from django.http import JsonResponse
import joblib
import numpy as np
import pandas as pd
from joblib import load
import os
from calendar import monthrange
import random
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from django.db.models import Avg, Count, Sum
from django.http import Http404
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LinearRegression
import pickle
import openai
import json
from django.utils.timezone import now

dataset_path = 'data/megaGymDataset.csv'
exercises_dataset = pd.read_csv(dataset_path)
print("Liczba ćwiczeń w dataset:", exercises_dataset.shape)
print("Kolumny w dataset:", exercises_dataset.columns)

def evaluate_models_view(request):
    dataset_path = 'data/training_data.csv'

    try:
        data = pd.read_csv(dataset_path)

        data['Gender'] = LabelEncoder().fit_transform(data['Gender'])
        data['Workout_Type'] = LabelEncoder().fit_transform(data['Workout_Type'])

        X = data[['Age', 'Gender', 'Weight (kg)', 'Height (m)', 'Max_BPM', 'Avg_BPM',
                  'Resting_BPM', 'Fat_Percentage', 'Water_Intake (liters)', 'Experience_Level', 'BMI']]
        y_workout_type = data['Workout_Type']
        y_duration = data['Session_Duration (hours)']
        y_calories = data['Calories_Burned']

        X_train, X_test, y_workout_train, y_workout_test = train_test_split(X, y_workout_type, test_size=0.2, random_state=42)
        _, _, y_duration_train, y_duration_test = train_test_split(X, y_duration, test_size=0.2, random_state=42)
        _, _, y_calories_train, y_calories_test = train_test_split(X, y_calories, test_size=0.2, random_state=42)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        workout_type_model = RandomForestClassifier(random_state=42)
        workout_type_model.fit(X_train_scaled, y_workout_train)
        y_workout_pred = workout_type_model.predict(X_test_scaled)
        workout_accuracy = accuracy_score(y_workout_test, y_workout_pred)
        workout_report = classification_report(y_workout_test, y_workout_pred, output_dict=True)

        formatted_report = [
            {
                'class': label,
                'precision': metrics['precision'],
                'recall': metrics['recall'],
                'f1_score': metrics['f1-score']
            }
            for label, metrics in workout_report.items() if label.isdigit()
        ]

        duration_model = LinearRegression()
        duration_model.fit(X_train_scaled, y_duration_train)
        y_duration_pred = duration_model.predict(X_test_scaled)
        duration_r2 = r2_score(y_duration_test, y_duration_pred)
        duration_rmse = np.sqrt(mean_squared_error(y_duration_test, y_duration_pred))

        calories_model = RandomForestRegressor(random_state=42)
        calories_model.fit(X_train_scaled, y_calories_train)
        y_calories_pred = calories_model.predict(X_test_scaled)
        calories_r2 = r2_score(y_calories_test, y_calories_pred)
        calories_rmse = np.sqrt(mean_squared_error(y_calories_test, y_calories_pred))

        context = {
            'workout_accuracy': round(workout_accuracy * 100, 2),
            'workout_report': formatted_report,
            'duration_r2': round(duration_r2, 2),
            'duration_rmse': round(duration_rmse, 2),
            'calories_r2': round(calories_r2, 2),
            'calories_rmse': round(calories_rmse, 2),
        }
        return render(request, 'trening/evaluate_models.html', context)

    except Exception as e:
        return render(request, 'trening/evaluate_models.html', {'error': str(e)})

openai.api_key = os.environ.get("OPENAI_API_KEY")

def fitness_chat_page(request):
    return render(request, "trening/fitness_chat.html")

@csrf_exempt
def fitness_chat(request):
    if request.method == "POST":
        if not openai.api_key:
            return JsonResponse({"error": "Brak konfiguracji OPENAI_API_KEY."}, status=503)

        data = json.loads(request.body)
        user_message = data.get("message", "")

        if not user_message:
            return JsonResponse({"error": "Wpisz wiadomość!"}, status=400)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  
                messages=[
                    {"role": "system", "content": "Jesteś ekspertem fitness. Udzielasz porad dotyczących treningów, diety i zdrowia."},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            gpt_response = response["choices"][0]["message"]["content"]

            return JsonResponse({"response": gpt_response}, status=200)

        except openai.error.OpenAIError as e:
            return JsonResponse({"error": f"Błąd OpenAI: {str(e)}"}, status=500)

        except Exception as e:
            return JsonResponse({"error": f"Błąd serwera: {str(e)}"}, status=500)

    return JsonResponse({"error": "Metoda POST jest wymagana"}, status=405)

User = get_user_model()

def home_view(request):
    """Widok strony głównej"""
    return render(request, 'trening/home.html')

def login_view(request):
    """Widok logowania użytkownika"""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Witaj ponownie, {user.first_name}!')

            if not hasattr(user, "profile") or not user.profile.profile_completed:
                return redirect('trening:user_data')  

            return redirect('trening:dashboard')  
        else:
            messages.error(request, 'Nieprawidłowe dane logowania. Spróbuj ponownie.')
    else:
        form = AuthenticationForm()

    return render(request, 'trening/login.html', {'form': form})


def register_view(request):
    """Widok rejestracji użytkownika"""
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, 'Hasła nie są zgodne. Spróbuj ponownie.')
            return render(request, 'trening/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Użytkownik z podanym adresem email już istnieje.')
            return render(request, 'trening/register.html')

        try:
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                gender=gender,
                password=password1
            )
            user.save()
            messages.success(request, 'Rejestracja zakończona sukcesem! Możesz się teraz zalogować.')
            return redirect('trening:login')
        except Exception as e:
            messages.error(request, f'Wystąpił błąd podczas rejestracji: {str(e)}')

    return render(request, 'trening/register.html')

@login_required
def user_dashboard(request):
    today = date.today()
    user = request.user

    duplicates = DailyUserStats.objects.filter(user=user, date=today)
    if duplicates.count() > 1:
        duplicates.exclude(id=duplicates.first().id).delete()

    daily_stats, created = DailyUserStats.objects.get_or_create(user=user, date=today)

    if request.method == "POST":
        weight = request.POST.get("weight")
        calorie_balance = request.POST.get("calorie_balance")
        hydration = request.POST.get("hydration")

        try:
            if weight:
                daily_stats.weight = float(weight)
            if calorie_balance:
                daily_stats.calorie_balance = int(calorie_balance)
            if hydration:
                daily_stats.hydration = float(hydration)
            daily_stats.save()
            messages.success(request, "Twoje dane dnia zostały zaktualizowane.")
        except ValueError:
            messages.error(request, "Wprowadzono nieprawidłowe dane.")

        return redirect("trening:dashboard")

    unread_notifications = Notification.objects.filter(user=user, is_read=False)

    context = {
        "today_trainings": TrainingSession.objects.filter(session_date=today, user=user),
        "today": today,
        "day_of_week": today.strftime('%A'),
        "daily_stats": daily_stats,
        "unread_notifications": unread_notifications,  
    }

    return render(request, 'trening/dashboard.html', context)


@csrf_exempt
@login_required
def update_hydration(request):
    if request.method == 'POST':
        hydration = float(request.POST.get('hydration', 0))
        today = date.today()
        daily_plan = DailyPlan.objects.filter(user=request.user, date=today).first()
        if daily_plan:
            daily_plan.hydration_level += hydration
            daily_plan.save()
    return HttpResponseRedirect(reverse('trening:dashboard'))

def generate_calendar_days(year, month):
    """Generuje listę wszystkich dni w podanym miesiącu."""
    start_date = date(year, month, 1)
    days_in_month = (date(year, month + 1, 1) - start_date).days if month < 12 else 31
    return [start_date + timedelta(days=i) for i in range(days_in_month)]


def training_plan(request, year=None, month=None):
    today = date.today()
    year = year or today.year
    month = month or today.month

    _, num_days = calendar.monthrange(year, month)
    calendar_days = [date(year, month, day) for day in range(1, num_days + 1)]

    trainings = TrainingSession.objects.filter(
        user=request.user,
        session_date__year=year,
        session_date__month=month
    )

    completed_trainings = trainings.filter(completed=True).order_by("session_date")

    training_list = []
    for day in calendar_days:
        training = trainings.filter(session_date=day).first()  
        training_list.append((day, training))

    context = {
        "calendar_days": calendar_days,
        "training_list": training_list,
        "completed_trainings": completed_trainings,  
        "current_year": year,
        "month_name": calendar.month_name[month],
        "prev_month": month - 1 if month > 1 else 12,
        "prev_year": year - 1 if month == 1 else year,
        "next_month": month + 1 if month < 12 else 1,
        "next_year": year + 1 if month == 12 else year,
    }
    return render(request, "trening/training_plan.html", context)

def delete_training(request, session_id):
    """
    Widok do usuwania treningu na podstawie jego ID.
    """
    training = get_object_or_404(TrainingSession, id=session_id, user=request.user)
    training.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Trening został usunięty.'})
    return redirect('trening:training_plan')

def data_analysis(request):
    user = request.user
    today = datetime.now().date()

    week_offset = int(request.GET.get('week', 0))  
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    weekly_stats = DailyUserStats.objects.filter(
        user=user, date__range=[start_of_week, end_of_week]
    ).order_by('date')

    monthly_stats = DailyUserStats.objects.filter(
        user=user, date__range=[start_of_month, end_of_month]
    ).order_by('date')

    def generate_full_date_range(start_date, end_date):
        return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    def prepare_chart_data(stats, date_range):
        data = {date: {'calorie_balance': 0, 'hydration': 0, 'weight': 0} for date in date_range}

        for stat in stats:
            data[stat.date] = {
                'calorie_balance': stat.calorie_balance or 0,
                'hydration': stat.hydration or 0,
                'weight': stat.weight or 0,
            }

        return {
            'dates': [date.strftime('%Y-%m-%d') for date in date_range],
            'calorie_balance': [data[date]['calorie_balance'] for date in date_range],
            'hydration': [data[date]['hydration'] for date in date_range],
            'weight': [data[date]['weight'] for date in date_range],
        }

    weekly_date_range = generate_full_date_range(start_of_week, end_of_week)
    monthly_date_range = generate_full_date_range(start_of_month, end_of_month)

    weekly_chart_data = prepare_chart_data(weekly_stats, weekly_date_range)
    monthly_chart_data = prepare_chart_data(monthly_stats, monthly_date_range)

    def summarize_data(stats):
        if not stats.exists():
            return {
                'weight_change': 0,
                'avg_calories': 0,
                'avg_hydration': 0,
            }

        first_stat = stats.order_by('date').first()
        last_stat = stats.order_by('date').last()
        weight_change = (last_stat.weight or 0) - (first_stat.weight or 0)

        avg_calories = stats.aggregate(avg_calories=Avg('calorie_balance'))['avg_calories'] or 0
        avg_hydration = stats.aggregate(avg_hydration=Avg('hydration'))['avg_hydration'] or 0

        return {
            'weight_change': round(weight_change, 2),
            'avg_calories': round(avg_calories, 2),
            'avg_hydration': round(avg_hydration, 2),
        }

    weekly_summary = summarize_data(weekly_stats)
    monthly_summary = summarize_data(monthly_stats)

    context = {
        'weekly_summary': weekly_summary,
        'monthly_summary': monthly_summary,
        'weekly_chart_data': weekly_chart_data,
        'monthly_chart_data': monthly_chart_data,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'week_offset': week_offset,
    }

    return render(request, 'trening/data_analysis.html', context)

NEW_CALORIES_MODEL_PATH = 'trening/ml_models/new_calories_model.pkl'
NEW_WEIGHT_MODEL_PATH = 'trening/ml_models/new_weight_model.pkl'
NEW_SCALER_PATH = 'trening/ml_models/new_scaler.pkl'


def analyze_new_predictions(user):
    """
    Generuje prognozy na podstawie danych z bazy i nowych modeli ML.
    """
    with open(NEW_CALORIES_MODEL_PATH, 'rb') as f:
        new_calories_model = pickle.load(f)
    with open(NEW_WEIGHT_MODEL_PATH, 'rb') as f:
        new_weight_model = pickle.load(f)
    with open(NEW_SCALER_PATH, 'rb') as f:
        new_scaler = pickle.load(f)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    stats = DailyUserStats.objects.filter(
        user=user,
        date__range=[start_date, end_date]
    ).values('calorie_balance', 'hydration', 'weight')

    if not stats.exists():
        return {
            'calorie_predictions': [],
            'weight_change_prediction': 0,
        }

    data = list(stats)
    features = np.array([[d['calorie_balance'], d['hydration'], d['weight']] for d in data])
    features = np.nan_to_num(features)  

    scaled_features = new_scaler.transform(features)

    calorie_predictions = new_calories_model.predict(scaled_features)
    weight_change_prediction = new_weight_model.predict(scaled_features).sum()

    return {
        'calorie_predictions': calorie_predictions.tolist(),
        'weight_change_prediction': round(weight_change_prediction, 2),
    }


def new_data_analysis(request):
    """
    Widok analizy danych – prognoza spożycia kalorii i zmiany wagi na podstawie danych z bazy.
    """
    user = request.user

    predictions = analyze_new_predictions(user)

    context = {
        'future_predictions': {
            'calories': predictions['calorie_predictions'],
            'weight_change': predictions['weight_change_prediction'],
        },
    }

    return render(request, 'trening/new_data_analysis.html', context)

@login_required
def training_detail(request, date):
    from datetime import datetime
    
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d").date()
    
    trainings = TrainingSession.objects.filter(session_date=date, user=request.user)
    print(f"Trainings for date {date}: {trainings}")  

    daily_stats = DailyUserStats.objects.filter(user=request.user, date=date)

    if daily_stats.exists():
        if daily_stats.count() > 1:
            daily_stats = daily_stats.first()
            print(f"WARNING: Multiple DailyUserStats found for user {request.user} and date {date}. Using the first one.")
        else:
            daily_stats = daily_stats.first()
    else:
        daily_stats = DailyUserStats.objects.create(user=request.user, date=date)

    if request.method == "POST":
        print("POST data:", request.POST) 

        if 'training_id' in request.POST:
            training_id = request.POST.get("training_id")
            training = get_object_or_404(TrainingSession, id=training_id, user=request.user)
            print(f"Training ID: {training_id}, Training: {training}")  

            if 'mark_completed' in request.POST:  
                training.completed = True
                training.save()
                print("Training marked as completed.")  
                messages.success(request, "Trening został oznaczony jako odbyty.")
                return redirect("trening:training_detail", date=date)

            elif 'update_actual_data' in request.POST:  
                actual_duration = request.POST.get("actual_duration")
                actual_calories = request.POST.get("actual_calories")
                actual_avg_bpm = request.POST.get("actual_avg_bpm")
                actual_max_bpm = request.POST.get("actual_max_bpm")
                comments = request.POST.get("comments")

                print(f"Actual data received: duration={actual_duration}, calories={actual_calories}, "
                      f"avg_bpm={actual_avg_bpm}, max_bpm={actual_max_bpm}, comments={comments}")  

                if not all([actual_duration, actual_calories, actual_avg_bpm, actual_max_bpm]):
                    messages.error(request, "Wszystkie pola muszą być wypełnione.")
                    print("Validation failed: Missing data.")  
                    return redirect("trening:training_detail", date=date)

                report, created = TrainingReport.objects.get_or_create(
                    training=training,
                    defaults={
                        'actual_duration': actual_duration,
                        'actual_calories': actual_calories,
                        'actual_avg_bpm': actual_avg_bpm,
                        'actual_max_bpm': actual_max_bpm,
                        'comments': comments,
                    }
                )
                if not created:
                    report.actual_duration = actual_duration
                    report.actual_calories = actual_calories
                    report.actual_avg_bpm = actual_avg_bpm
                    report.actual_max_bpm = actual_max_bpm
                    report.comments = comments
                    report.save()
                print(f"Training report updated: {report}")  

                messages.success(request, "Dane treningu zostały zaktualizowane.")
                return redirect("trening:training_detail", date=date)

            elif 'delete_training' in request.POST:  
                training.delete()
                print("Training deleted.")  
                messages.success(request, "Trening został usunięty.")
                return redirect("trening:training_detail", date=date)

        elif 'update_stats' in request.POST:  
            weight = request.POST.get("weight")
            calories_consumed = request.POST.get("calories_consumed")
            hydration = request.POST.get("hydration")

            print(f"Daily stats data received: weight={weight}, calories_consumed={calories_consumed}, hydration={hydration}")  

            if not all([weight, calories_consumed, hydration]):
                messages.error(request, "Wszystkie pola muszą być wypełnione.")
                print("Validation failed: Missing daily stats data.")  
                return redirect("trening:training_detail", date=date)

            daily_stats.date = date
            daily_stats.weight = float(weight)
            daily_stats.calories_consumed = int(calories_consumed)
            daily_stats.hydration = float(hydration)

            total_calories_burned = sum(
                report.actual_calories for report in TrainingReport.objects.filter(training__session_date=date, training__user=request.user)
            )
            daily_stats.calorie_balance = daily_stats.calories_consumed - total_calories_burned
            daily_stats.save()

            print(f"Daily stats updated: {daily_stats}")  
            messages.success(request, "Twoje dane dnia zostały zaktualizowane.")
            return redirect("trening:training_detail", date=date)

    trainings_with_reports = [
        {
            'training': training,
            'report': training.reports.first()  
        }
        for training in trainings
    ]
    print(f"Trainings with reports: {trainings_with_reports}")  

    analysis_data = []
    for training_data in trainings_with_reports:
        training = training_data['training']
        report = training_data['report']
        if report:
            analysis_data.append({
                'workout_type': training.workout_type,
                'recommended_duration': training.session_duration,
                'actual_duration': report.actual_duration,
                'recommended_calories': training.calories_burned,
                'actual_calories': report.actual_calories,
                'recommended_avg_bpm': training.avg_bpm,
                'actual_avg_bpm': report.actual_avg_bpm,
            })

    total_calories_burned = sum(
        report.actual_calories for report in TrainingReport.objects.filter(training__session_date=date, training__user=request.user)
    )
    analysis_data.append({
        'type': 'Daily Stats',
        'calories_consumed': daily_stats.calories_consumed,
        'calories_burned': total_calories_burned,
        'calorie_balance': daily_stats.calorie_balance,
        'hydration': daily_stats.hydration,
    })

    return render(request, "trening/training_detail.html", {
        "selected_date": date,
        "trainings_with_reports": trainings_with_reports,
        "analysis_data": analysis_data,
        "session": trainings.first() if trainings.exists() else None,
        "daily_stats": daily_stats,
    })

def monthly_report(request, year, month):
    user = request.user
    start_date = date(year, month, 1)
    end_date = date(year, month, 1).replace(month=month % 12 + 1) - timedelta(days=1)

    reports = TrainingReport.objects.filter(
        training__user=user,
        training__session_date__range=[start_date, end_date]
    )

    summary = reports.aggregate(
        total_duration=Sum('actual_duration'),
        total_calories=Sum('actual_calories'),
        avg_avg_bpm=Avg('actual_avg_bpm'),
        avg_max_bpm=Avg('actual_max_bpm')
    )

    return render(request, "trening/monthly_report.html", {
        "reports": reports,
        "summary": summary,
        "year": year,
        "month": month
    })

@login_required
@login_required
def user_data(request):
    """
    Wyświetla dane biometryczne i preferencje użytkownika. Umożliwia edycję każdego atrybutu osobno.
    """
    body_metric, _ = BodyMetric.objects.get_or_create(
        user=request.user,
        defaults={
            'weight_kg': 70.0,
            'height_m': 1.75,
            'water_intake_liters': 2.0,
        }
    )

    user_preference, _ = UserPreference.objects.get_or_create(
        user=request.user,
        defaults={
            'workout_frequency': 1,
            'experience_level': 1,
            'goal': 'Poprawa kondycji',
        }
    )

    if request.method == 'POST':
        field_name = request.POST.get("field_name")
        field_value = request.POST.get("field_value")

        if 'update_body_metric' in request.POST and hasattr(body_metric, field_name):
            setattr(body_metric, field_name, field_value)
            body_metric.save()

        elif 'update_user_preference' in request.POST and hasattr(user_preference, field_name):
            setattr(user_preference, field_name, field_value)
            user_preference.save()

        return redirect('trening:user_data')

    context = {
        'body_metric': body_metric,
        'user_preference': user_preference,
    }
    return render(request, 'trening/user_data.html', context)

def edit_user_data(request):
    """
    Edits existing biometric data for the user.
    """
    try:
        body_metric = request.user.body_metric
    except BodyMetric.DoesNotExist:
        return redirect('trening:user_data')

    if request.method == 'POST':
        form = BodyMetricForm(request.POST, instance=body_metric)
        if form.is_valid():
            form.save()
            return redirect('trening:user_data')
    else:
        form = BodyMetricForm(instance=body_metric)

    return render(request, 'trening/edit_user_data.html', {'form': form})

model_dir = 'trening/ml_models'
workout_type_model = joblib.load(f"{model_dir}/workout_type_model.pkl")
duration_model = joblib.load(f"{model_dir}/duration_model.pkl")
calories_model = joblib.load(f"{model_dir}/calories_model.pkl")
frequency_model = joblib.load(f"{model_dir}/frequency_model.pkl")
scaler = joblib.load(f"{model_dir}/scaler.pkl")
one_hot_encoder = joblib.load(f"{model_dir}/one_hot_encoder.pkl")

def validate_user_data(user_data):
    required_fields = [
        'age', 'gender', 'weight_kg', 'height_m', 'bmi',
        'max_bpm', 'avg_bpm', 'resting_bpm', 'fat_percentage',
        'water_intake', 'experience_level'
    ]
    for field in required_fields:
        if field not in user_data or user_data[field] is None:
            raise ValueError(f"Missing required field: {field}")
        return redirect('trening:user_data')
    print("User Data Validated:", user_data)

def generate_workout_plan(user_data):
    try:
        print("\n=== Starting Weekly Structured Workout Plan Generation ===")

        validate_user_data(user_data)

        input_data = pd.DataFrame([{
            'Age': user_data['age'],
            'Gender': 1 if user_data['gender'] == 'Male' else 0,
            'Weight (kg)': user_data['weight_kg'],
            'Height (m)': user_data['height_m'],
            'BMI': user_data['bmi'],
            'Max_BPM': user_data['max_bpm'],
            'Avg_BPM': user_data['avg_bpm'],
            'Resting_BPM': user_data['resting_bpm'],
            'Fat_Percentage': user_data['fat_percentage'],
            'Water_Intake (liters)': user_data['water_intake'],
            'Experience_Level': user_data['experience_level']
        }])

        print("Input Data Prepared:")
        print(input_data)

        expected_features = scaler.feature_names_in_
        input_data = input_data[expected_features]

        input_scaled = scaler.transform(input_data)
        if input_scaled.ndim == 1:
            input_scaled = input_scaled.reshape(1, -1)

        print("Input Scaled Shape:", input_scaled.shape)
        print("Input Scaled Data:", input_scaled)

        duration = duration_model.predict(input_scaled)
        calories = calories_model.predict(input_scaled)

        workout_types = {
            0: 'Strength Training',  
            2: 'Cardio',             
            4: 'HIIT',               
            6: 'Mobility and Stretching'  
        }

        workout_plan = []
        today = datetime.now()
        current_year, current_month = today.year, today.month
        _, days_in_month = calendar.monthrange(current_year, current_month)

        for day in range(1, days_in_month + 1):
            current_date = datetime(current_year, current_month, day)
            day_of_week = current_date.weekday()  

            if day_of_week in workout_types:
                workout_type = workout_types[day_of_week]
                adjusted_duration = duration[0] * random.uniform(0.8, 1.2)
                adjusted_calories = calories[0] * random.uniform(0.8, 1.2)
                workout_plan.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'workout_type': workout_type,
                    'duration': round(adjusted_duration, 1),
                    'calories': round(adjusted_calories),
                })
            else:
                workout_plan.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'workout_type': 'Recovery',
                    'duration': 0,
                    'calories': 0,
                })

        print("Workout Plan Generated Successfully:")
        for entry in workout_plan:
            print(entry)

        return workout_plan

    except Exception as e:
        print(f"Error in generate_workout_plan: {e}")

        print("Generating Fallback Plan...")
        fallback_plan = [{
            'date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
            'workout_type': 'General Fitness',
            'duration': 30,
            'calories': 200
        } for i in range(28)]
        print("Fallback Plan Generated:")
        for entry in fallback_plan:
            print(entry)
        return fallback_plan

def get_workout_plan(request):
    if request.method == 'POST':
        try:
            body_metric = request.user.body_metric
            user_preference = request.user.preferences
        except (AttributeError, BodyMetric.DoesNotExist, UserPreference.DoesNotExist):
            messages.error(request, "Najpierw uzupełnij swoje dane biometryczne i preferencje.")
            return redirect('trening:user_data')

        if not body_metric.bmi and body_metric.height_m > 0:
            body_metric.bmi = body_metric.weight_kg / (body_metric.height_m ** 2)
            body_metric.save()

        try:
            user_data = {
                'age': body_metric.age,
                'gender': 'Male' if body_metric.gender == 'Mężczyzna' else 'Female',
                'weight_kg': body_metric.weight_kg,
                'height_m': body_metric.height_m,
                'bmi': body_metric.bmi,
                'max_bpm': body_metric.max_bpm,
                'avg_bpm': body_metric.avg_bpm,
                'resting_bpm': body_metric.resting_bpm,
                'fat_percentage': body_metric.fat_percentage or 0,
                'water_intake': body_metric.water_intake_liters,
                'experience_level': user_preference.experience_level
            }

            workout_plan = generate_workout_plan(user_data)

            training_plan = TrainingPlan.objects.create(user=request.user, date_created=datetime.now())

            for session in workout_plan:
                TrainingSession.objects.create(
                    user=request.user,
                    session_date=session['date'],  
                    workout_type=session['workout_type'],
                    session_duration=session['duration'],  
                    calories_burned=session['calories'],  
                    avg_bpm=70,  
                    max_bpm=180,
                    resting_bpm=60
                )


            messages.success(request, "Plan treningowy został zapisany.")
            return redirect('trening:training_plan')

        except Exception as e:
            print(f"Error generating plan: {e}")
            messages.error(request, f"Wystąpił błąd podczas generowania planu: {e}")
            return redirect('trening:generate_plan')

    return render(request, 'trening/generate_plan.html')

def get_exercises_by_type(training_type, dataset, user, date):
    print(f"Filtruję dla typu treningu: {training_type}")

    filtered_exercises = dataset[dataset['Type'].str.contains(training_type, case=False, na=False)]
    print(f"Znaleziono ćwiczenia: {filtered_exercises.shape[0]}")

    if len(filtered_exercises) > 5:
        filtered_exercises = filtered_exercises.sample(5)
        print(f"Losowo wybrane ćwiczenia: {filtered_exercises.shape[0]}")

    return filtered_exercises[['Title', 'Desc', 'BodyPart', 'Equipment', 'Level']]


def generate_exercise_plan(training_type, dataset, count=5):
    """
    Generowanie losowego planu ćwiczeń na podstawie rodzaju treningu.
    """
    exercises = get_exercises_by_type(training_type, dataset)
    return exercises.sample(count) 

from django.shortcuts import render
@login_required
def training_details_view(request, workout_type):
    try:
        selected_date = request.GET.get('date', None)
        if selected_date:
            try:
                selected_date = datetime.strptime(selected_date, '%b. %d, %Y').date()
            except ValueError:
                raise ValueError(f"Nieprawidłowy format daty: {selected_date}")
        else:
            selected_date = datetime.now().date()

        print(f"Typ treningu: {workout_type}")
        print(f"Data treningu: {selected_date}")

        exercises = get_exercises_by_type(workout_type, exercises_dataset, request.user, selected_date)
        print(f"Ćwiczenia do wyświetlenia: {exercises}")

        for _, exercise in exercises.iterrows():
            ExerciseHistory.objects.get_or_create(
                user=request.user,
                exercise_title=exercise['Title'],
                date=selected_date
            )

        return render(request, 'trening/training_details.html', {
            'workout_type': workout_type,
            'selected_date': selected_date,
            'exercises': exercises.to_dict(orient='records')
        })
    except ValueError as e:
        print(f"Error: {str(e)}")
        return render(request, 'trening/training_details.html', {
            'error': f"Błąd: {str(e)}"
        })
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return render(request, 'trening/training_details.html', {
            'error': f"Wystąpił błąd: {str(e)}"
        })

def mark_training_as_completed(request, session_id):
    training = get_object_or_404(TrainingSession, id=session_id, user=request.user)
    training.completed = True
    training.save()
    return JsonResponse({'status': 'success', 'message': 'Training marked as completed!'})

def logout_view(request):
    if request.method == "POST" or request.method == "GET":
        logout(request)
        return redirect('trening:dashboard')  
    return redirect('trening:dashboard')  

def update_weight_goals(user):
    last_weight_entry = DailyUserStats.objects.filter(user=user).order_by('-date').first()
    if not last_weight_entry or not last_weight_entry.weight:
        return

    last_weight = last_weight_entry.weight
    weight_goals = TrainingGoal.objects.filter(user=user, goal_type="weight_loss", is_completed=False)

    for goal in weight_goals:
        goal.current_progress = last_weight

        if last_weight <= goal.target_value:
            goal.is_completed = True
            messages.success(user, f"Osiągnąłeś cel: {goal.get_goal_type_display()}!")

        goal.save()

def update_daily_stats(request, date):
    if request.method == "POST":
        weight = request.POST.get("weight")
        calories_consumed = request.POST.get("calories_consumed")
        hydration = request.POST.get("hydration")

        daily_stats, created = DailyUserStats.objects.get_or_create(user=request.user, date=date)

        daily_stats.weight = float(weight) if weight else None
        daily_stats.calories_consumed = int(calories_consumed) if calories_consumed else None
        daily_stats.hydration = float(hydration) if hydration else None

        total_calories_burned = sum(
            report.actual_calories for report in TrainingReport.objects.filter(training__session_date=date, training__user=request.user)
        )
        daily_stats.calorie_balance = daily_stats.calories_consumed - total_calories_burned if daily_stats.calories_consumed else None
        daily_stats.save()

        update_weight_goals(request.user)

        messages.success(request, "Twoje dane dnia zostały zaktualizowane.")
        return redirect("trening:training_detail", date=date)

def goals_and_rewards(request):
    active_goals = TrainingGoal.objects.filter(user=request.user, is_completed=False)
    completed_goals = TrainingGoal.objects.filter(user=request.user, is_completed=True)

    last_daily_stats = DailyUserStats.objects.filter(user=request.user).order_by('-date').first()
    last_weight = last_daily_stats.weight if last_daily_stats else None

    for goal in active_goals:
        previous_status = goal.is_completed  
        if goal.goal_type == "weight_loss" and last_weight is not None:
            goal.current_progress = last_weight
            if last_weight < goal.target_value:  
                goal.is_completed = True
        elif goal.goal_type == "muscle_gain" and last_weight is not None:
            goal.current_progress = last_weight
            if last_weight >= goal.target_value:  
                goal.is_completed = True
        else:
            goal.update_progress()

        if goal.is_completed and not previous_status:
            Notification.objects.create(
                user=request.user,
                message=f"Gratulacje! Ukończyłeś cel: {goal.get_goal_type_display()}."
            )
            goal.save()

    rewards_assigned = Reward.assign_for_training_completion(request.user)

    for reward in rewards_assigned:
        Notification.objects.create(
            user=request.user,
            message=f"Zdobyłeś nową nagrodę: {reward.description}!"
        )

    rewards = Reward.objects.filter(user=request.user)

    if request.method == "POST":
        # Dodawanie nowego celu
        if "add_goal" in request.POST:
            goal_type = request.POST.get("goal_type")
            target_value = float(request.POST.get("target_value"))
            deadline = request.POST.get("deadline")

            TrainingGoal.objects.create(
                user=request.user,
                goal_type=goal_type,
                target_value=target_value,
                deadline=deadline,
            )
            Notification.objects.create(
                user=request.user,
                message=f"Utworzyłeś nowy cel: {goal_type}."
            )
            messages.success(request, "Nowy cel treningowy został dodany!")
            return redirect("trening:goals_and_rewards")

        if "redeem_reward" in request.POST:
            reward_id = request.POST.get("reward_id")
            reward = Reward.objects.get(id=reward_id, user=request.user)
            if not reward.is_redeemed:
                reward.is_redeemed = True
                reward.save()
                Notification.objects.create(
                    user=request.user,
                    message=f"Zrealizowałeś nagrodę: {reward.description}."
                )
                messages.success(request, f"Nagroda '{reward.description}' została zrealizowana!")
            else:
                messages.error(request, "Ta nagroda została już wcześniej zrealizowana.")
            return redirect("trening:goals_and_rewards")

    print(f"Active goals: {active_goals}")
    print(f"Completed goals: {completed_goals}")
    print(f"Rewards: {rewards}")
    print(f"Last weight: {last_weight}")

    return render(request, "trening/goals_and_rewards.html", {
        "active_goals": active_goals,
        "completed_goals": completed_goals,
        "rewards": rewards,
        "last_weight": last_weight,
    })

@login_required
def mark_notification_as_read(request, notification_id):
    """Oznacz powiadomienie jako przeczytane."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('trening:dashboard')  

def create_notification(user, message):
    Notification.objects.create(user=user, message=message)
