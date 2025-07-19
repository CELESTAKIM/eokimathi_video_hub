# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Video, Comment, Feedback, Notification

# Register your models here.

# Inline for UserProfile to be managed directly from User admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'

# Extend UserAdmin to include UserProfile
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_main_admin_display', 'is_restricted_admin_display')
    list_filter = ('is_staff', 'is_active', 'userprofile__is_main_admin', 'userprofile__is_restricted_admin')
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('is_main_admin_from_profile', 'is_restricted_admin_from_profile')}),
    )

    def is_main_admin_display(self, obj):
        return obj.userprofile.is_main_admin
    is_main_admin_display.boolean = True
    is_main_admin_display.short_description = 'Main Admin'

    def is_restricted_admin_display(self, obj):
        return obj.userprofile.is_restricted_admin
    is_restricted_admin_display.boolean = True
    is_restricted_admin_display.short_description = 'Restricted Admin'

    # Custom methods to get/set boolean fields from UserProfile
    # This maps the UserProfile boolean fields to the UserAdmin form
    def is_main_admin_from_profile(self, obj):
        return obj.userprofile.is_main_admin
    is_main_admin_from_profile.short_description = 'Is Main Admin'
    is_main_admin_from_profile.boolean = True

    def set_is_main_admin_from_profile(self, obj, value):
        obj.userprofile.is_main_admin = value
        obj.userprofile.save()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.userprofile.is_main_admin and obj.username == 'celestakim': # Replace with actual main admin username
            # Prevent non-main admins from changing main admin status
            if not request.user.userprofile.is_main_admin:
                if 'is_main_admin_from_profile' in form.base_fields:
                    form.base_fields['is_main_admin_from_profile'].disabled = True
                if 'is_staff' in form.base_fields: # Also prevent changing staff status for the main admin
                    form.base_fields['is_staff'].disabled = True
        return form

    # Proxy property for is_main_admin_from_profile
    def _get_is_main_admin(self, obj):
        return obj.userprofile.is_main_admin
    def _set_is_main_admin(self, obj, value):
        if obj.userprofile: # Ensure profile exists
            obj.userprofile.is_main_admin = value
            obj.userprofile.save()
    is_main_admin_from_profile = property(_get_is_main_admin, _set_is_main_admin)

    # Proxy property for is_restricted_admin_from_profile
    def _get_is_restricted_admin(self, obj):
        return obj.userprofile.is_restricted_admin
    def _set_is_restricted_admin(self, obj, value):
        if obj.userprofile: # Ensure profile exists
            obj.userprofile.is_restricted_admin = value
            obj.userprofile.save()
    is_restricted_admin_from_profile = property(_get_is_restricted_admin, _set_is_restricted_admin)


# Re-register User model
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'admin', 'video_type', 'uploaded_at', 'views', 'get_likes_count')
    list_filter = ('video_type', 'uploaded_at', 'tags', 'admin')
    search_fields = ('title', 'description', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('views', 'get_likes_count', 'uploaded_at')

    def get_likes_count(self, obj):
        return obj.likes.count()
    get_likes_count.short_description = 'Likes'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('video', 'user', 'text', 'created_at')
    list_filter = ('created_at', 'user', 'video')
    search_fields = ('text', 'user__username', 'video__title')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at', 'user', 'video')
    search_fields = ('message', 'subject', 'user__username', 'video__title')
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} feedback messages marked as read.")
    mark_as_read.short_description = "Mark selected feedback as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} feedback messages marked as unread.")
    mark_as_unread.short_description = "Mark selected feedback as unread"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at', 'user')
    search_fields = ('message', 'user__username')
    actions = ['mark_as_read', 'mark_as_unread'] # Reuse actions for notifications

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} notifications marked as read.")
    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} notifications marked as unread.")
    mark_as_unread.short_description = "Mark selected notifications as unread"