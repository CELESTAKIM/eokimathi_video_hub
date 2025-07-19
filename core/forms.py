# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, Video, Comment, Feedback, Notification
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name',)

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            UserProfile.objects.create(user=user) # Create a UserProfile when a new user registers
        return user

class UserLoginForm(AuthenticationForm):
    # This form is fine as is, Django's built-in AuthenticationForm is good.
    # We can add crispy forms helper if desired for better styling.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'password',
            Submit('submit', 'Login', css_class='btn btn-primary w-100 mt-3')
        )

class UserProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'email',
            'bio',
            'profile_picture',
            Submit('submit', 'Update Profile', css_class='btn btn-success w-100 mt-3')
        )

    def save(self, commit=True):
        user_profile = super().save(commit=False)
        user = user_profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            user_profile.save()
        return user_profile

class VideoUploadForm(forms.ModelForm):
    tags = forms.CharField(
        max_length=500,
        help_text="Comma-separated tags (e.g., GIS, Remote Sensing)",
        widget=forms.TextInput(attrs={'placeholder': 'Enter tags like GIS, Cartography, Survey'})
    )

    class Meta:
        model = Video
        fields = ['title', 'description', 'video_type', 'video_file', 'video_url', 'tags']
        widgets = {
            'video_type': forms.RadioSelect(choices=Video.ADMIN_ROLES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            'tags',
            'video_type',
            'video_file',
            'video_url',
            Submit('submit', 'Upload Video', css_class='btn btn-primary w-100 mt-3')
        )
        # Add JavaScript to toggle visibility of video_file and video_url based on video_type
        self.fields['video_file'].widget.attrs.update({'class': 'video-file-field'})
        self.fields['video_url'].widget.attrs.update({'class': 'video-url-field'})

        if not self.instance.pk: # For creation, default to file upload visible
            self.fields['video_url'].required = False
            self.fields['video_file'].required = True
        else: # For editing, handle existing values
            if self.instance.video_type == 'file':
                self.fields['video_url'].required = False
                self.fields['video_file'].required = True
            else:
                self.fields['video_file'].required = False
                self.fields['video_url'].required = True

    def clean(self):
        cleaned_data = super().clean()
        video_type = cleaned_data.get('video_type')
        video_file = cleaned_data.get('video_file')
        video_url = cleaned_data.get('video_url')

        if video_type == 'file' and not video_file:
            self.add_error('video_file', 'This field is required for file uploads.')
        if video_type == 'link' and not video_url:
            self.add_error('video_url', 'This field is required for external links.')
        if video_type == 'file' and video_url:
            self.add_error('video_url', 'Cannot provide a URL for a file upload type.')
        if video_type == 'link' and video_file:
            self.add_error('video_file', 'Cannot upload a file for an external link type.')

        return cleaned_data


class VideoEditForm(forms.ModelForm):
    tags = forms.CharField(
        max_length=500,
        help_text="Comma-separated tags (e.g., GIS, Remote Sensing)",
        widget=forms.TextInput(attrs={'placeholder': 'Enter tags like GIS, Cartography, Survey'})
    )
    # Allow replacing video file/url if admin wants
    new_video_file = forms.FileField(required=False, label="Replace Video File")
    new_video_url = forms.URLField(max_length=500, required=False, label="Replace Video URL",
                                   help_text="Enter a URL for external videos (e.g., YouTube, Vimeo embed URL)")
    new_thumbnail = forms.ImageField(required=False, label="Replace Thumbnail")


    class Meta:
        model = Video
        fields = ['title', 'description', 'tags'] # Removed video_file, video_url, thumbnail for replacement fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            'tags',
            'new_video_file',
            'new_video_url',
            'new_thumbnail',
            Submit('submit', 'Update Video', css_class='btn btn-success w-100 mt-3')
        )

    def clean(self):
        cleaned_data = super().clean()
        new_video_file = cleaned_data.get('new_video_file')
        new_video_url = cleaned_data.get('new_video_url')

        # Logic for allowing replacement:
        # If new_video_file is provided, clear new_video_url (and vice versa)
        if new_video_file and new_video_url:
            raise forms.ValidationError("You can only replace with either a new video file OR a new video URL, not both.")
        return cleaned_data

    def save(self, commit=True):
        video = super().save(commit=False)
        new_video_file = self.cleaned_data.get('new_video_file')
        new_video_url = self.cleaned_data.get('new_video_url')
        new_thumbnail = self.cleaned_data.get('new_thumbnail')

        if new_video_file:
            video.video_file = new_video_file
            video.video_url = None
            video.video_type = 'file'
            video.thumbnail = None # Trigger new thumbnail generation in Video model's save method
        elif new_video_url:
            video.video_url = new_video_url
            video.video_file = None
            video.video_type = 'link'
            video.thumbnail = None # Admin needs to manually upload or system needs to fetch from URL if possible
        if new_thumbnail:
            video.thumbnail = new_thumbnail

        if commit:
            video.save()
        return video


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your comment here...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'text',
            Submit('submit', 'Post Comment', css_class='btn btn-info mt-2')
        )

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Your detailed feedback...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'subject',
            'message',
            Submit('submit', 'Send Feedback', css_class='btn btn-success mt-2')
        )

class NotificationForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select Users"
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter your notification message here...'}),
        label="Notification Message"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'users',
            'message',
            Submit('submit', 'Send Notifications', css_class='btn btn-primary mt-3')
        )

class AdminUserProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    is_main_admin = forms.BooleanField(required=False, label="Is Main Admin (Can manage other admins)")
    is_restricted_admin = forms.BooleanField(required=False, label="Is Restricted Admin")

    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture']

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user', None) # Pass the requesting user to the form
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['is_main_admin'].initial = self.instance.is_main_admin
            self.fields['is_restricted_admin'].initial = self.instance.is_restricted_admin

        # Restrict 'is_main_admin' checkbox: only the actual main admin can set/unset it
        if request_user and not request_user.userprofile.is_main_admin:
            self.fields['is_main_admin'].widget.attrs['disabled'] = True
            # If the user being edited IS the main admin, no one else can change their admin status
            if self.instance.is_main_admin:
                 self.fields['is_restricted_admin'].widget.attrs['disabled'] = True

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'email',
            'bio',
            'profile_picture',
            'is_main_admin',
            'is_restricted_admin',
            Submit('submit', 'Update User', css_class='btn btn-success w-100 mt-3')
        )

    def save(self, commit=True):
        user_profile = super().save(commit=False)
        user = user_profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        # Only update if the field is not disabled (i.e., if current user is main admin)
        if 'is_main_admin' in self.cleaned_data and not self.fields['is_main_admin'].widget.attrs.get('disabled'):
            user_profile.is_main_admin = self.cleaned_data['is_main_admin']
        if 'is_restricted_admin' in self.cleaned_data and not self.fields['is_restricted_admin'].widget.attrs.get('disabled'):
            user_profile.is_restricted_admin = self.cleaned_data['is_restricted_admin']

        if commit:
            user.save()
            user_profile.save()
        return user_profile