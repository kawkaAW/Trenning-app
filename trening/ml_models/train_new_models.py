import os
import django
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'treningapp.settings')  
django.setup()

from trening.models import DailyUserStats  


stats = DailyUserStats.objects.all().values('calorie_balance', 'hydration', 'weight', 'weight_change', 'target_calories')
data = list(stats)

if not data:
    print("Brak danych w bazie!")
    exit()


X = np.array([[d['calorie_balance'], d['hydration'], d['weight']] for d in data])
y_calories = np.array([d['target_calories'] for d in data])  
y_weight = np.array([d['weight_change'] for d in data])  


scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)


X_train, X_test, y_cal_train, y_cal_test = train_test_split(X_scaled, y_calories, test_size=0.2, random_state=42)
X_train_w, X_test_w, y_w_train, y_w_test = train_test_split(X_scaled, y_weight, test_size=0.2, random_state=42)


calories_model = LinearRegression()
calories_model.fit(X_train, y_cal_train)

weight_model = LinearRegression()
weight_model.fit(X_train_w, y_w_train)


with open('trening/ml_models/new_calories_model.pkl', 'wb') as f:
    pickle.dump(calories_model, f)

with open('trening/ml_models/new_weight_model.pkl', 'wb') as f:
    pickle.dump(weight_model, f)

with open('trening/ml_models/new_scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

print("Modele zostały wytrenowane i zapisane!")
