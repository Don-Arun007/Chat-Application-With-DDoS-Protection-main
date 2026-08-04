from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_list_view, name='chat_list'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/<str:username>/', views.chat_room_view, name='chat_room'),
    path('start-chat/<int:user_id>/', views.start_chat_view, name='start_chat'),
]