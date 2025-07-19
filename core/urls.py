# core/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # For Django's default login/logout views if not custom

urlpatterns = [
    # Public / Auth
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # User Features
    path('dashboard/', views.user_dashboard_view, name='user_dashboard'),
    path('video/<slug:slug>/', views.video_detail_view, name='video_detail'),
    path('video/<slug:slug>/like/', views.like_video, name='like_video'), # AJAX endpoint
    path('profile/update/', views.profile_update_view, name='profile_update'),


    # Admin Dashboard
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin_dashboard/videos/', views.admin_video_list_view, name='admin_video_list'),
    path('admin_dashboard/videos/upload/', views.admin_video_upload_view, name='admin_video_upload'),
    path('admin_dashboard/videos/edit/<int:pk>/', views.admin_video_edit_view, name='admin_video_edit'),
    path('admin_dashboard/videos/delete/<int:pk>/', views.admin_video_delete_view, name='admin_video_delete'),
    path('admin_dashboard/videos/add_likes/<int:pk>/', views.admin_video_add_likes_view, name='admin_video_add_likes'),

    path('admin_dashboard/users/', views.admin_user_list_view, name='admin_user_list'),
    path('admin_dashboard/users/edit/<int:pk>/', views.admin_user_edit_view, name='admin_user_edit'),
    path('admin_dashboard/users/delete/<int:pk>/', views.admin_user_delete_view, name='admin_user_delete'),
    path('admin_dashboard/users/download_csv/', views.admin_download_users_csv, name='admin_download_users_csv'),

    path('admin_dashboard/feedback/', views.admin_feedback_list_view, name='admin_feedback_list'),
    path('admin_dashboard/feedback/<int:pk>/toggle_read/', views.admin_feedback_mark_read_toggle, name='admin_feedback_mark_read_toggle'),
    path('admin_dashboard/feedback/<int:pk>/delete/', views.admin_feedback_delete, name='admin_feedback_delete'),

    path('admin_dashboard/notifications/send/', views.admin_send_notification_view, name='admin_send_notification'),

    # Static Pages
    path('terms/', views.terms_view, name='terms'),
    path('donate/', views.donate_view, name='donate'),
]