import logging

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CommentForm, QuestionForm, SignupForm
from .models import Comment, Question, Vote

logger = logging.getLogger(__name__)


def question_list(request):
    questions = (
        Question.objects.select_related('author')
        .prefetch_related('comments')
        .annotate(score=Count('votes'))
        .order_by('-score', '-created_at')
    )
    if request.user.is_authenticated:
        questions = questions.annotate(
            has_voted=Exists(Vote.objects.filter(question=OuterRef('pk'), user=request.user))
        )
    return render(request, 'questions/question_list.html', {'questions': questions})


def question_detail(request, pk):
    question = get_object_or_404(
        Question.objects.select_related('author')
        .prefetch_related('comments__author')
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
                author=request.user,
                body=form.cleaned_data['body'],
                parent=reply_parent,
            )
            return redirect('question_detail_slug', slug=question.slug)
    else:
        form = CommentForm()

    comments = list(question.comments.select_related('author').order_by('created_at'))
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
        Question.objects.select_related('author').prefetch_related('comments__author'),
        slug=slug,
    )
    return question_detail(request, question.pk)


@login_required
def question_upvote(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method != 'POST':
        return redirect('question_detail_slug', slug=question.slug)
    Vote.objects.get_or_create(question=question, user=request.user)
    next_url = request.POST.get('next') or reverse('question_detail_slug', args=[question.slug])
    return redirect(next_url)


@login_required
def question_create(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.author = request.user
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
