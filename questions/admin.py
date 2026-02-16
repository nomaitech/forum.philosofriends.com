from django.contrib import admin

from .models import Comment, Profile, Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'author', 'created_at', 'pinned')
    search_fields = ('title', 'body', 'author__username')
    list_filter = ('pinned',)
    ordering = ('-pinned', '-created_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('question', 'author', 'parent', 'created_at')
    search_fields = ('body', 'author__username', 'question__title')
    ordering = ('-created_at',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'is_vip',
        'notify_new_posts',
        'notify_replies_to_comments',
        'notify_replies_to_posts',
    )
    search_fields = ('user__username', 'user__email')
    list_filter = (
        'is_vip',
        'notify_new_posts',
        'notify_replies_to_comments',
        'notify_replies_to_posts',
    )
