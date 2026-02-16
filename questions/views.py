import logging
import socket
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from .forms import AccountDeletionForm, CommentForm, ProfileSettingsForm, QuestionForm, SignupForm
from .models import Comment, Question, Vote

logger = logging.getLogger(__name__)
IMPERSONATION_USER_ID_SESSION_KEY = 'admin_impersonation_user_id'


class _TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ''

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'title':
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()


def fetch_link_title(url):
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'}:
        return url
    request = Request(
        url,
        headers={
            'User-Agent': 'PhilosofriendsLinkBot/1.0',
            'Accept': 'text/html,application/xhtml+xml',
        },
    )
    try:
        with urlopen(request, timeout=5) as response:
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                return url
            charset = response.headers.get_content_charset() or 'utf-8'
            body = response.read(200_000)
            parser = _TitleParser()
            parser.feed(body.decode(charset, errors='ignore'))
            title = parser.title or url
            return title.strip()[:180] or url
    except (URLError, TimeoutError, socket.timeout, ValueError):
        return url


def get_impersonated_user(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return None
    user_id = request.session.get(IMPERSONATION_USER_ID_SESSION_KEY)
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.pop(IMPERSONATION_USER_ID_SESSION_KEY, None)
        return None


def get_posting_user(request):
    return get_impersonated_user(request) or request.user




def _format_question_date(created_at, now):
    delta_seconds = max((now - created_at).total_seconds(), 0.0)
    if delta_seconds < 86400:
        if delta_seconds < 60:
            return "just now"
        total_minutes = int(delta_seconds // 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours:
            unit = "hour" if hours == 1 else "hours"
            return f"{hours} {unit} ago"
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit} ago"
    return date_format(timezone.localtime(created_at), "M j, Y")


def question_list(request):
    sort = request.GET.get('sort')
    now = timezone.now()
    questions = (
        Question.objects.select_related('author', 'author__profile')
        .prefetch_related('comments')
        .annotate(score=Count('votes', distinct=True), comments_count=Count('comments', distinct=True))
    )
    if request.user.is_authenticated:
        questions = questions.annotate(
            has_voted=Exists(Vote.objects.filter(question=OuterRef('pk'), user=request.user))
        )
    if sort == 'new':
        questions = questions.order_by('-pinned', '-created_at', '-score')
    else:
        gravity = 1.8
        base_offset = 2.0
        questions = list(questions)
        for question in questions:
            age_hours = max((now - question.created_at).total_seconds() / 3600.0, 0.0)
            points = question.score or 0
            comments = question.comments_count or 0
            question.rank_score = (points + 0.8 * comments) / pow(age_hours + base_offset, gravity)
        questions.sort(
            key=lambda item: (
                0 if item.pinned else 1,
                -(item.rank_score or 0.0),
                -(item.score or 0),
                -item.created_at.timestamp(),
            )
        )
    questions = list(questions)
    for question in questions:
        question.display_date = _format_question_date(question.created_at, now)
    return render(request, 'questions/question_list.html', {'questions': questions})


def profile_detail(request, username):
    profile_user = get_object_or_404(
        User.objects.select_related('profile'),
        username=username,
    )
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    if request.method == 'POST':
        if not is_own_profile:
            return redirect('profile_detail', username=profile_user.username)
        settings_form = ProfileSettingsForm(profile_user, profile_user.profile, request.POST)
        if settings_form.is_valid():
            settings_form.save()
            return redirect('profile_detail', username=profile_user.username)
    elif is_own_profile:
        settings_form = ProfileSettingsForm(profile_user, profile_user.profile)
    else:
        settings_form = None

    questions = (
        Question.objects.filter(author=profile_user)
        .select_related('author', 'author__profile')
        .annotate(score=Count('votes', distinct=True), comments_count=Count('comments', distinct=True))
        .order_by('-pinned', '-created_at')
    )
    return render(
        request,
        'questions/profile.html',
        {
            'profile_user': profile_user,
            'questions': questions,
            'is_own_profile': is_own_profile,
            'settings_form': settings_form,
        },
    )


def question_detail(request, pk):
    question = get_object_or_404(
        Question.objects.select_related('author', 'author__profile')
        .prefetch_related('comments__author', 'comments__author__profile')
        .annotate(score=Count('votes')),
        pk=pk,
    )
    user_has_voted = False
    if request.user.is_authenticated:
        user_has_voted = Vote.objects.filter(question=question, user=request.user).exists()
    if question.slug:
        canonical_url = reverse('question_detail_slug', args=[question.slug])
        if request.path != canonical_url:
            return redirect(canonical_url, permanent=True)
    reply_parent = None
    if request.method == 'POST':
        if not request.user.is_authenticated:
            login_next = reverse('question_detail_slug', args=[question.slug])
            return redirect(f'/accounts/login/?next={login_next}')
        form = CommentForm(request.POST)
        parent_id = request.POST.get('parent_id') or None
        if parent_id:
            try:
                reply_parent = question.comments.get(pk=parent_id)
            except Comment.DoesNotExist:
                reply_parent = None
        if form.is_valid():
            Comment.objects.create(
                question=question,
                author=get_posting_user(request),
                body=form.cleaned_data['body'],
                parent=reply_parent,
            )
            return redirect('question_detail_slug', slug=question.slug)
    else:
        form = CommentForm()

    comments = list(question.comments.select_related('author', 'author__profile').order_by('created_at'))
    comment_map = {}
    for comment in comments:
        comment_map.setdefault(comment.parent_id, []).append(comment)

    def build_comment_tree(parent_id=None):
        nodes = []
        for comment in comment_map.get(parent_id, []):
            comment.children = build_comment_tree(comment.id)
            nodes.append(comment)
        return nodes

    comment_tree = build_comment_tree()
    return render(
        request,
        'questions/question_detail.html',
        {
            'question': question,
            'comments': comment_tree,
            'comment_form': form,
            'reply_parent_id': reply_parent.id if reply_parent else None,
            'reply_parent_author': reply_parent.author.username if reply_parent else None,
            'user_has_voted': user_has_voted,
        },
    )


def question_detail_slug(request, slug):
    question = get_object_or_404(
        Question.objects.select_related('author', 'author__profile')
        .prefetch_related('comments__author', 'comments__author__profile'),
        slug=slug,
    )
    return question_detail(request, question.pk)


@login_required
def comment_edit(request, pk):
    comment = get_object_or_404(Comment.objects.select_related('question'), pk=pk)
    if request.user != comment.author and not request.user.is_superuser:
        return redirect('question_detail_slug', slug=comment.question.slug)
    next_url = (
        request.POST.get('next')
        or request.GET.get('next')
        or reverse('question_detail_slug', args=[comment.question.slug])
    )
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect(next_url)
    else:
        form = CommentForm(instance=comment)
    return render(
        request,
        'questions/comment_edit.html',
        {
            'comment': comment,
            'question': comment.question,
            'form': form,
            'next_url': next_url,
        },
    )


@login_required
def question_upvote(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method != 'POST':
        return redirect('question_detail_slug', slug=question.slug)
    existing_vote = Vote.objects.filter(question=question, user=request.user)
    if existing_vote.exists():
        existing_vote.delete()
    else:
        Vote.objects.create(question=question, user=request.user)
    next_url = request.POST.get('next') or reverse('question_detail_slug', args=[question.slug])
    return redirect(next_url)


@login_required
def question_pin_toggle(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if not request.user.is_superuser or request.method != 'POST':
        return redirect('question_detail_slug', slug=question.slug)
    question.pinned = not question.pinned
    question.save(update_fields=['pinned'])
    next_url = request.POST.get('next') or reverse('question_detail_slug', args=[question.slug])
    return redirect(next_url)


@login_required
def question_create(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        post_type = request.POST.get('post_type', 'question')
        if post_type == 'link':
            form.fields['title'].required = False
            form.fields['body'].required = False
        if form.is_valid():
            question = form.save(commit=False)
            question.author = get_posting_user(request)
            if post_type == 'link':
                link = (form.cleaned_data.get('link') or '').strip()
                if not link:
                    form.add_error('link', 'Add a link URL.')
                else:
                    question.title = fetch_link_title(link)
                    question.body = ''
                    question.link = link
                    question.save()
                    return redirect('question_detail_slug', slug=question.slug)
            else:
                question.save()
                return redirect('question_detail_slug', slug=question.slug)
    else:
        form = QuestionForm()
    return render(request, 'questions/question_form.html', {'form': form})


def signup(request):
    if request.user.is_authenticated:
        return redirect('question_list')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
            except IntegrityError:
                username = form.cleaned_data.get('username')
                logger.exception("Signup failed due to IntegrityError for username=%s", username)
                form.add_error(
                    'username',
                    'That username is not available. Please choose another.',
                )
            else:
                login(request, user)
                return redirect('question_list')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


def logout_view(request):
    request.session.pop(IMPERSONATION_USER_ID_SESSION_KEY, None)
    logout(request)
    return redirect('question_list')


@login_required
def account_delete(request):
    user_to_delete = request.user
    if request.method == 'POST':
        form = AccountDeletionForm(user_to_delete, request.POST)
        if form.is_valid():
            logout(request)
            user_to_delete.delete()
            return redirect('question_list')
    else:
        form = AccountDeletionForm(user_to_delete)
    return render(request, 'registration/account_delete.html', {'form': form})


@login_required
def impersonate_start(request):
    if request.method != 'POST' or not request.user.is_superuser:
        return redirect('question_list')
    user_id = request.POST.get('user_id')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('question_list')
    target_user = User.objects.filter(pk=user_id).first()
    if not target_user:
        return redirect(next_url)
    request.session[IMPERSONATION_USER_ID_SESSION_KEY] = target_user.pk
    return redirect(next_url)


@login_required
def impersonate_stop(request):
    if request.method != 'POST' or not request.user.is_superuser:
        return redirect('question_list')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('question_list')
    request.session.pop(IMPERSONATION_USER_ID_SESSION_KEY, None)
    return redirect(next_url)
