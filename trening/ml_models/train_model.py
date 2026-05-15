import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import joblib


model_dir = 'trening/ml_models'
os.makedirs(model_dir, exist_ok=True)

data = pd.read_csv('data/training_data.csv')

data['Gender'] = data['Gender'].map({'Male': 1, 'Female': 0})

if data.isnull().sum().any():
    print("Brakujące wartości w danych, uzupełnianie braków...")
    data.fillna(data.mean(), inplace=True)  

one_hot_encoder = OneHotEncoder(sparse_output=False)
workout_type_encoded = one_hot_encoder.fit_transform(data[['Workout_Type']])


encoded_columns = one_hot_encoder.get_feature_names_out(['Workout_Type'])
data = data.join(pd.DataFrame(workout_type_encoded, columns=encoded_columns))
data.drop('Workout_Type', axis=1, inplace=True)


X = data[['Age', 'Gender', 'Weight (kg)', 'Height (m)', 'Max_BPM', 'Avg_BPM',
          'Resting_BPM', 'Fat_Percentage', 'Water_Intake (liters)', 'Experience_Level', 'BMI']]
y = data[['Session_Duration (hours)', 'Calories_Burned', 'Workout_Frequency (days/week)']]


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


y_duration_train = y_train['Session_Duration (hours)']
y_calories_train = y_train['Calories_Burned']
y_frequency_train = y_train['Workout_Frequency (days/week)']

y_duration_test = y_test['Session_Duration (hours)']
y_calories_test = y_test['Calories_Burned']
y_frequency_test = y_test['Workout_Frequency (days/week)']


workout_type_encoded_train = workout_type_encoded[:len(X_train)]
workout_type_encoded_test = workout_type_encoded[len(X_train):]


scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)


classifier = RandomForestClassifier(random_state=42)
classifier.fit(X_train_scaled, workout_type_encoded_train.argmax(axis=1))


reg_duration = GradientBoostingRegressor(random_state=42)
reg_duration.fit(X_train_scaled, y_duration_train)


reg_calories = RandomForestRegressor(random_state=42)
reg_calories.fit(X_train_scaled, y_calories_train)


reg_frequency = GradientBoostingRegressor(random_state=42)
reg_frequency.fit(X_train_scaled, y_frequency_train)


joblib.dump(classifier, os.path.join(model_dir, 'workout_type_model.pkl'))
joblib.dump(reg_duration, os.path.join(model_dir, 'duration_model.pkl'))
joblib.dump(reg_calories, os.path.join(model_dir, 'calories_model.pkl'))
joblib.dump(reg_frequency, os.path.join(model_dir, 'frequency_model.pkl'))
joblib.dump(scaler, os.path.join(model_dir, 'scaler.pkl'))
joblib.dump(one_hot_encoder, os.path.join(model_dir, 'one_hot_encoder.pkl'))

print("All models trained and saved successfully.")
