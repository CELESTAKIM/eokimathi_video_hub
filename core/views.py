# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import csv
import json
import asyncio # For async operations with channels if needed
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import UserProfile, Video, Comment, Feedback, Notification
from .forms import (
    UserRegisterForm, UserLoginForm, UserProfileUpdateForm,
    VideoUploadForm, VideoEditForm, CommentForm, FeedbackForm,
    NotificationForm, AdminUserProfileEditForm
)

# --- Helper Functions for Admin Restrictions ---
def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.userprofile.is_main_admin or user.userprofile.is_restricted_admin)

def is_main_admin(user):
    return user.is_authenticated and user.userprofile.is_main_admin

def is_restricted_admin(user):
    return user.is_authenticated and user.userprofile.is_restricted_admin

# --- Public & User Authentication Views ---

def home_view(request):
    # For non-logged-in users, show thumbnails and titles only
    all_tags = Video.get_all_tags()
    selected_tag = request.GET.get('tag')

    if selected_tag:
        videos = Video.objects.filter(tags__icontains=selected_tag).order_by('-uploaded_at')
    else:
        videos = Video.objects.all().order_by('-uploaded_at')

    # Pagination
    paginator = Paginator(videos, 12) # Show 12 videos per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_obj': page_obj,
        'all_tags': all_tags,
        'selected_tag': selected_tag,
    }
    return render(request, 'core/index.html', context)

def register_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard') # Redirect if already logged in
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            # After registration, check if it's the first user to make them main admin
            if User.objects.count() == 1:
                profile = user.userprofile
                profile.is_main_admin = True
                profile.is_restricted_admin = True # Main admin is also a restricted admin by default
                profile.save()
                messages.info(request, "You are the first user, so you've been granted Main Admin privileges.")
            return redirect('user_dashboard')
        else:
            messages.error(request, "Registration failed. Please correct the errors.")
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                # Redirect admins to admin dashboard, regular users to user dashboard
                if is_admin_user(user):
                    return redirect('admin_dashboard')
                else:
                    return redirect('user_dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

# --- User Dashboard & Video Playback ---

@login_required
def user_dashboard_view(request):
    user_videos = Video.objects.filter(admin=request.user).order_by('-uploaded_at') # Videos uploaded by this user
    # Or, if this dashboard is for general user consumption:
    all_videos = Video.objects.all().order_by('-uploaded_at')

    all_tags = Video.get_all_tags()
    selected_tag = request.GET.get('tag')
    search_query = request.GET.get('q')

    if selected_tag:
        all_videos = all_videos.filter(tags__icontains=selected_tag)
    if search_query:
        all_videos = all_videos.filter(
            models.Q(title__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(tags__icontains=search_query)
        )

    paginator = Paginator(all_videos, 12)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    context = {
        'page_obj': page_obj,
        'all_tags': all_tags,
        'selected_tag': selected_tag,
        'search_query': search_query,
        'user_profile': user_profile,
    }
    return render(request, 'core/user_dashboard.html', context)

@login_required
def video_detail_view(request, slug):
    video = get_object_or_404(Video, slug=slug)
    comments = video.comments.all()

    # Increment view count
    video.views += 1
    video.save()

    # Comment Form
    if request.method == 'POST' and 'comment_form_submit' in request.POST:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.video = video
            new_comment.user = request.user
            new_comment.save()
            messages.success(request, "Your comment has been posted!")
            return redirect('video_detail', slug=slug)
        else:
            messages.error(request, "Failed to post comment. Please correct errors.")
    else:
        comment_form = CommentForm()

    # Feedback Form (for admin)
    feedback_form = FeedbackForm()
    if request.method == 'POST' and 'feedback_form_submit' in request.POST:
        feedback_form = FeedbackForm(request.POST)
        if feedback_form.is_valid():
            new_feedback = feedback_form.save(commit=False)
            new_feedback.video = video
            new_feedback.user = request.user
            new_feedback.save()
            messages.success(request, "Your feedback has been sent to the admin!")
            return redirect('video_detail', slug=slug)
        else:
            messages.error(request, "Failed to send feedback. Please correct errors.")

    is_liked = video.likes.filter(id=request.user.id).exists()

    context = {
        'video': video,
        'comments': comments,
        'comment_form': comment_form,
        'feedback_form': feedback_form,
        'is_liked': is_liked,
    }
    return render(request, 'core/video_detail.html', context)

@login_required
@require_POST
def like_video(request, slug):
    video = get_object_or_404(Video, slug=slug)
    if request.user.is_authenticated:
        if video.likes.filter(id=request.user.id).exists():
            video.likes.remove(request.user)
            liked = False
            message = "Video unliked."
        else:
            video.likes.add(request.user)
            liked = True
            message = "Video liked!"
        return JsonResponse({'liked': liked, 'likes_count': video.likes.count(), 'message': message})
    return JsonResponse({'error': 'Authentication required'}, status=401)

@login_required
def profile_update_view(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('profile_update')
        else:
            messages.error(request, "Profile update failed. Please correct errors.")
    else:
        form = UserProfileUpdateForm(instance=user_profile)
    return render(request, 'core/profile_update.html', {'form': form})

# --- Admin Dashboard Views ---

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_dashboard_view(request):
    total_users = User.objects.count()
    total_videos = Video.objects.count()
    total_likes = Video.objects.aggregate(total_likes=Count('likes'))['total_likes']
    total_comments = Comment.objects.count()
    total_feedback = Feedback.objects.count()
    unread_feedback = Feedback.objects.filter(is_read=False).count()

    # Data for charts (prepare as JSON for frontend Chart.js)
    # Example 1: Videos per Tag (Pie Chart)
    video_tags_data = Video.objects.values('tags').annotate(count=Count('id')).order_by('-count')
    tags_labels = []
    tags_counts = []
    for entry in video_tags_data:
        # Split comma-separated tags and count individually
        for tag in [t.strip() for t in entry['tags'].split(',') if t.strip()]:
            if tag not in tags_labels:
                tags_labels.append(tag)
                tags_counts.append(1) # Start with 1 if new tag
            else:
                tags_counts[tags_labels.index(tag)] += 1 # Increment existing count

    # Example 2: Videos Uploaded over Time (Line Chart)
    video_upload_dates = Video.objects.extra({'date': "date(uploaded_at)"}).values('date').annotate(count=Count('id')).order_by('date')
    upload_labels = [str(entry['date']) for entry in video_upload_dates]
    upload_counts = [entry['count'] for entry in video_upload_dates]

    # Example 3: Most Viewed Videos (Bar Chart)
    most_viewed_videos = Video.objects.order_by('-views')[:5]
    viewed_labels = [v.title for v in most_viewed_videos]
    viewed_counts = [v.views for v in most_viewed_videos]

    context = {
        'total_users': total_users,
        'total_videos': total_videos,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'total_feedback': total_feedback,
        'unread_feedback': unread_feedback,
        'tags_chart_data': json.dumps({'labels': tags_labels, 'data': tags_counts}),
        'upload_chart_data': json.dumps({'labels': upload_labels, 'data': upload_counts}),
        'viewed_chart_data': json.dumps({'labels': viewed_labels, 'data': viewed_counts}),
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_video_upload_view(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.admin = request.user
            video.save()
            messages.success(request, f"Video '{video.title}' uploaded successfully!")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Video upload failed. Please correct errors.")
    else:
        form = VideoUploadForm()
    return render(request, 'core/admin_video_upload.html', {'form': form})

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_video_list_view(request):
    videos = Video.objects.all().order_by('-uploaded_at')
    # Add search and filter if needed
    paginator = Paginator(videos, 10) # 10 videos per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {'page_obj': page_obj}
    return render(request, 'core/admin_video_list.html', context)

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_video_edit_view(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if request.method == 'POST':
        form = VideoEditForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            messages.success(request, f"Video '{video.title}' updated successfully!")
            return redirect('admin_video_list')
        else:
            messages.error(request, "Video update failed. Please correct errors.")
    else:
        form = VideoEditForm(instance=video)
    return render(request, 'core/admin_video_edit.html', {'form': form, 'video': video})

@login_required
@user_passes_test(is_admin_user, login_url='home')
@require_POST
def admin_video_delete_view(request, pk):
    video = get_object_or_404(Video, pk=pk)
    video.delete()
    messages.success(request, f"Video '{video.title}' deleted successfully.")
    return redirect('admin_video_list')

@login_required
@user_passes_test(is_admin_user, login_url='home')
@require_POST
def admin_video_add_likes_view(request, pk):
    video = get_object_or_404(Video, pk=pk)
    try:
        num_likes = int(request.POST.get('num_likes', 0))
        if num_likes > 0:
            # This is a simplified way to add "likes". In a real system,
            # you might create dummy User objects or a separate `FictionalLike` model.
            # For demonstration, we'll just increment a 'fake_likes' field or similar.
            # Since likes is ManyToMany, adding many dummy users would be complex.
            # Let's adjust the Video model to have a `manual_likes_count` for this purpose.
            # For now, we'll just show a message.
            messages.info(request, f"Admin added {num_likes} 'mock' likes to '{video.title}'. (Feature needs model adjustment)")
            # To actually reflect this in the dashboard, you might add a field to Video model:
            # `manual_likes = models.PositiveIntegerField(default=0)`
            # Then: `video.manual_likes += num_likes` and `video.save()`
            # And in dashboard, display `video.likes.count() + video.manual_likes`
    except ValueError:
        messages.error(request, "Invalid number of likes.")
    return redirect('admin_video_list')


@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_user_list_view(request):
    users = User.objects.select_related('userprofile').order_by('username')
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    context = {'page_obj': page_obj}
    return render(request, 'core/admin_user_list.html', context)

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_user_edit_view(request, pk):
    user_to_edit = get_object_or_404(User, pk=pk)
    user_profile_to_edit, created = UserProfile.objects.get_or_create(user=user_to_edit)

    if request.method == 'POST':
        # Pass the requesting user to the form for permission checks
        form = AdminUserProfileEditForm(request.POST, request.FILES, instance=user_profile_to_edit, request_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{user_to_edit.username}' profile updated successfully!")
            return redirect('admin_user_list')
        else:
            messages.error(request, "User profile update failed. Please correct errors.")
    else:
        form = AdminUserProfileEditForm(instance=user_profile_to_edit, request_user=request.user)

    context = {
        'form': form,
        'user_to_edit': user_to_edit,
    }
    return render(request, 'core/admin_user_edit.html', context)

@login_required
@user_passes_test(is_admin_user, login_url='home')
@require_POST
def admin_user_delete_view(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)

    # Prevent main admin from deleting themselves or other main admins
    # Ensure current request.user is a main admin to delete anyone
    if not request.user.userprofile.is_main_admin:
        messages.error(request, "You do not have permission to delete users.")
        return redirect('admin_user_list')

    # Main admin cannot delete themselves
    if user_to_delete.pk == request.user.pk:
        messages.error(request, "You cannot delete your own admin account.")
        return redirect('admin_user_list')

    # Main admin cannot delete another main admin
    if user_to_delete.userprofile.is_main_admin:
        messages.error(request, "You cannot delete another main admin account.")
        return redirect('admin_user_list')

    user_to_delete.delete()
    messages.success(request, f"User '{user_to_delete.username}' deleted successfully.")
    return redirect('admin_user_list')


@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_feedback_list_view(request):
    feedback_list = Feedback.objects.all().order_by('-created_at')
    paginator = Paginator(feedback_list, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    context = {'page_obj': page_obj}
    return render(request, 'core/admin_feedback_list.html', context)

@login_required
@user_passes_test(is_admin_user, login_url='home')
@require_POST
def admin_feedback_mark_read_toggle(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    feedback.is_read = not feedback.is_read
    feedback.save()
    messages.success(request, f"Feedback from {feedback.user.username} marked as {'read' if feedback.is_read else 'unread'}.")
    return redirect('admin_feedback_list')

@login_required
@user_passes_test(is_admin_user, login_url='home')
@require_POST
def admin_feedback_delete(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    feedback.delete()
    messages.success(request, f"Feedback from {feedback.user.username} deleted.")
    return redirect('admin_feedback_list')

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_send_notification_view(request):
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            selected_users = form.cleaned_data['users']
            message = form.cleaned_data['message']

            channel_layer = get_channel_layer()
            for user in selected_users:
                Notification.objects.create(user=user, message=message)
                # Send real-time notification via WebSocket (if user is connected)
                async_to_sync(channel_layer.group_send)(
                    f"user_{user.id}",
                    {
                        "type": "send_notification", # Corresponds to consumer method
                        "message": message,
                    }
                )
            messages.success(request, f"Notifications sent to {len(selected_users)} users.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Failed to send notifications. Please correct errors.")
    else:
        form = NotificationForm()
    return render(request, 'core/admin_send_notification.html', {'form': form})

@login_required
@user_passes_test(is_admin_user, login_url='home')
def admin_download_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_data.csv"'

    writer = csv.writer(response)
    # Header row
    writer.writerow(['ID', 'Username', 'Email', 'First Name', 'Last Name', 'Date Joined', 'Is Active', 'Is Staff', 'Is Superuser', 'Is Main Admin', 'Is Restricted Admin', 'Bio'])

    users = User.objects.all().select_related('userprofile')
    for user in users:
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            user.date_joined.strftime('%Y-%m-%d %H:%M:%S'), # Format datetime
            'Yes' if user.is_active else 'No',
            'Yes' if user.is_staff else 'No',
            'Yes' if user.is_superuser else 'No',
            'Yes' if hasattr(user, 'userprofile') and user.userprofile.is_main_admin else 'No',
            'Yes' if hasattr(user, 'userprofile') and user.userprofile.is_restricted_admin else 'No',
            user.userprofile.bio if hasattr(user, 'userprofile') else ''
        ])
    return response

# --- Static/Informational Pages ---
def terms_view(request):
    return render(request, 'core/terms.html')

def donate_view(request):
    mpesa_paybill = "0101370035" # Your M-Pesa Paybill Number
    mpesa_account_name = "EOKIMATHI" # Your M-Pesa Account Name

    context = {
        'mpesa_paybill': mpesa_paybill,
        'mpesa_account_name': mpesa_account_name,
    }
    return render(request, 'core/donate.html', context)