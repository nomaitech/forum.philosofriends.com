from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, QuestionForm, SignupForm
from .models import Comment, Question


def question_list(request):
    questions = Question.objects.select_related('author').prefetch_related('comments').order_by('-created_at')
    return render(request, 'questions/question_list.html', {'questions': questions})


def question_detail(request, pk):
    question = get_object_or_404(
        Question.objects.select_related('author').prefetch_related('comments__author'),
        pk=pk,
    )
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next=/questions/{pk}/')
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                question=question,
                author=request.user,
                body=form.cleaned_data['body'],
            )
            return redirect('question_detail', pk=pk)
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
        {'question': question, 'comments': comment_tree, 'comment_form': form},
    )


@login_required
def question_create(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.author = request.user
            question.save()
            return redirect('question_detail', pk=question.pk)
    else:
        form = QuestionForm()
    return render(request, 'questions/question_form.html', {'form': form})


def signup(request):
    if request.user.is_authenticated:
        return redirect('question_list')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('question_list')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})
