from django.urls import path

from . import views

urlpatterns = [
    path('', views.question_list, name='question_list'),
    path('questions/<int:pk>/', views.question_detail, name='question_detail'),
    path('questions/<int:pk>/upvote/', views.question_upvote, name='question_upvote'),
    path('questions/<int:pk>/pin/', views.question_pin_toggle, name='question_pin_toggle'),
    path('questions/<slug:slug>/', views.question_detail_slug, name='question_detail_slug'),
    path('submit/', views.question_create, name='question_create'),
    path('signup/', views.signup, name='signup'),
    path('account/delete/', views.account_delete, name='account_delete'),
]
