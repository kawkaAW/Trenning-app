from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'trening'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    path('update_hydration/', views.update_hydration, name='update_hydration'),
    path('training-plan/', views.training_plan, name='training_plan'),
    path('data-analysis/', views.data_analysis, name='data_analysis'),
    path('user-data/', views.user_data, name='user_data'),
    path('logout/', views.logout_view, name='logout'),
    path('training-detail/<str:date>/', views.training_detail, name='training_detail'),
    path('training-plan/<int:year>/<int:month>/', views.training_plan, name='training_plan'),
    path('delete-training/<int:session_id>/', views.delete_training, name='delete_training'),
    path('training-detail/<str:date>/', views.training_detail, name='training_detail'),
    path('user-data/', views.user_data, name='user_data'),
    path('user-data/edit/', views.edit_user_data, name='edit_user_data'),
    path('generate-plan/', views.get_workout_plan, name='generate_plan'),
    path('evaluate-models/', views.evaluate_models_view, name='evaluate_models'),
    path('training-details/<str:workout_type>/', views.training_details_view, name='training_details'),
    path('mark-completed/<int:session_id>/', views.mark_training_as_completed, name='mark_completed'),
    path('training-detail/<str:date>/', views.training_detail, name='training_detail'),
    path('new-data-analysis/', views.new_data_analysis, name='new_data_analysis'),
    path('chat/', views.fitness_chat_page, name='fitness_chat'),  
    path('fitness-chat/', views.fitness_chat, name='fitness_chat'),   
    path('chat/', views.fitness_chat_page, name='chat'),  
    path('fitness-chat/', views.fitness_chat, name='fitness_chat'),
    path("goals-and-rewards/", views.goals_and_rewards, name="goals_and_rewards"),
    path('mark-notification/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
]
