from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Comment, Question


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['title', 'link', 'body']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Ask a philosophical question'}),
            'link': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
            'body': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Add context if you want (optional)'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        link = (cleaned_data.get('link') or '').strip()
        title = (cleaned_data.get('title') or '').strip()
        if not title and not link:
            self.add_error('title', 'Add a question title or include a link.')
        return cleaned_data


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add a thoughtful comment'}),
        }


class AccountDeletionForm(forms.Form):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password to confirm'}),
        help_text='Enter your password to confirm account deletion.',
    )
    confirm = forms.BooleanField(
        label='I understand this action cannot be undone',
        required=True,
        help_text='All your questions, comments, and account data will be permanently deleted.',
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            if not self.user.check_password(password):
                raise ValidationError('Incorrect password. Please try again.')
        return password


class ProfileSettingsForm(forms.Form):
    email = forms.EmailField(
        required=False,
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
    )
    notify_new_posts = forms.BooleanField(required=False, label='New posts')
    notify_replies_to_comments = forms.BooleanField(required=False, label='New replies to your comments')
    notify_replies_to_posts = forms.BooleanField(required=False, label='New replies to your posts')

    def __init__(self, user, profile, *args, **kwargs):
        self.user = user
        self.profile = profile
        initial = kwargs.get('initial') or {}
        kwargs['initial'] = initial
        initial.setdefault('email', user.email)
        initial.setdefault('notify_new_posts', profile.notify_new_posts)
        initial.setdefault('notify_replies_to_comments', profile.notify_replies_to_comments)
        initial.setdefault('notify_replies_to_posts', profile.notify_replies_to_posts)
        super().__init__(*args, **kwargs)

    def save(self):
        self.user.email = self.cleaned_data['email']
        self.user.save(update_fields=['email'])
        self.profile.notify_new_posts = self.cleaned_data['notify_new_posts']
        self.profile.notify_replies_to_comments = self.cleaned_data['notify_replies_to_comments']
        self.profile.notify_replies_to_posts = self.cleaned_data['notify_replies_to_posts']
        self.profile.save(
            update_fields=[
                'notify_new_posts',
                'notify_replies_to_comments',
                'notify_replies_to_posts',
            ]
        )
