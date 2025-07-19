# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
import os
import moviepy.editor as mp # For video processing
from PIL import Image # For image manipulation
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_main_admin = models.BooleanField(default=False) # For the primary admin (CelestaKim)
    is_restricted_admin = models.BooleanField(default=False) # For other admins

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.profile_picture.path) # Overwrite original with resized

class Video(models.Model):
    ADMIN_ROLES = (
        ('file', 'File Upload'),
        ('link', 'External Link (YouTube, Vimeo, etc.)'),
    )

    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_videos')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    description = models.TextField()
    # If video_type is 'file', video_file is used. If 'link', video_url is used.
    video_type = models.CharField(max_length=10, choices=ADMIN_ROLES, default='file')
    video_file = models.FileField(upload_to='videos/', blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True,
                                help_text="Enter a URL for external videos (e.g., YouTube, Vimeo embed URL)")
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    tags = models.CharField(max_length=500, help_text="Comma-separated tags (e.g., GIS, Remote Sensing, Cartography)")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)
    # Using ManyToManyField for likes to track users who liked a video
    likes = models.ManyToManyField(User, related_name='liked_videos', blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('video_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug in case of duplicate titles
            original_slug = self.slug
            counter = 1
            while Video.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # Generate thumbnail from video file if it's a file upload and no thumbnail is provided
        if self.video_file and not self.thumbnail:
            try:
                # Save the video file temporarily to disk to be processed by moviepy
                # Use BytesIO to avoid saving to physical disk if storage is cloud-based
                temp_video_buffer = BytesIO(self.video_file.read())
                clip = mp.VideoFileClip(temp_video_buffer.name) # moviepy expects a file path
                frame = clip.get_frame(1) # Get frame at 1 second
                clip.close() # Important to close the clip to release resources

                image = Image.fromarray(frame)
                # Resize thumbnail
                output_size = (320, 180) # Common thumbnail size (16:9 aspect ratio)
                image.thumbnail(output_size, Image.Resampling.LANCZOS)

                thumb_io = BytesIO()
                image.save(thumb_io, format='JPEG', quality=85) # Save as JPEG for compression
                thumb_file_name = f"{self.slug}_thumb.jpg"
                self.thumbnail = InMemoryUploadedFile(
                    thumb_io, 'ImageField', thumb_file_name, 'image/jpeg',
                    thumb_io.tell(), None
                )
            except Exception as e:
                print(f"Error generating thumbnail: {e}")
                # Fallback or log error, maybe use a default thumbnail
                self.thumbnail = None # Ensure it's not set if generation fails

        super().save(*args, **kwargs)

    # Method to retrieve all unique tags from all videos
    @staticmethod
    def get_all_tags():
        tags = set()
        for video in Video.objects.values_list('tags', flat=True):
            if video:
                for tag in video.split(','):
                    tags.add(tag.strip().lower())
        return sorted(list(tags))


class Comment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.video.title[:30]}..."


class Feedback(models.Model):
    video = models.ForeignKey(Video, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_to_admin')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False) # Admin can mark as read

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback from {self.user.username} about {self.video.title if self.video else 'General'}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}..."