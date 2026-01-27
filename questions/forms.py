from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

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
        body = (cleaned_data.get('body') or '').strip()
        if not link and not body:
            self.add_error('body', 'Add context or include a link.')
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
