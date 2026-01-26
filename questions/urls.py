from django.urls import path

from . import views

urlpatterns = [
    path('', views.question_list, name='question_list'),
    path('questions/<int:pk>/', views.question_detail, name='question_detail'),
    path('questions/<slug:slug>/', views.question_detail_slug, name='question_detail_slug'),
    path('submit/', views.question_create, name='question_create'),
    path('signup/', views.signup, name='signup'),
]
