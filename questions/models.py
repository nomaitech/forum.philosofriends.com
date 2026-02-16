from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

class Question(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    body = models.TextField(blank=True)
    link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    pinned = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "question"
            slug = base_slug
            counter = 1
            while Question.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Vote(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['question', 'user'], name='unique_question_vote'),
        ]

    def __str__(self):
        return f'{self.user.username} upvoted {self.question.title}'


class Comment(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='replies', null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.author.username} on {self.question.title}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_vip = models.BooleanField(default=False, db_index=True)
    notify_new_posts = models.BooleanField(default=False)
    notify_replies_to_comments = models.BooleanField(default=False)
    notify_replies_to_posts = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} profile'


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=Question)
def send_new_post_notifications(sender, instance, created, **kwargs):
    if not created:
        return
    from .notifications import notify_new_question

    notify_new_question(instance)


@receiver(post_save, sender=Comment)
def send_reply_notifications(sender, instance, created, **kwargs):
    if not created:
        return
    from .notifications import notify_new_comment

    notify_new_comment(instance)
