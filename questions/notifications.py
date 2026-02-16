import json
import logging
import socket
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

logger = logging.getLogger(__name__)


def _notifications_enabled():
    return bool(getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False) and getattr(settings, 'SMTP2GO_API_KEY', ''))


def _question_url(question):
    site_url = getattr(settings, 'SITE_URL', 'https://forum.philosofriends.com').rstrip('/')
    return f"{site_url}{reverse('question_detail_slug', args=[question.slug])}"


def _send_smtp2go_email(to_email, subject, text_body):
    if not _notifications_enabled():
        return False

    payload = {
        'api_key': settings.SMTP2GO_API_KEY,
        'sender': settings.SMTP2GO_FROM_EMAIL,
        'to': [to_email],
        'subject': subject,
        'text_body': text_body,
    }
    request = Request(
        settings.SMTP2GO_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status < 400
    except (URLError, TimeoutError, socket.timeout, ValueError) as exc:
        logger.exception("Failed to send SMTP2GO email to %s: %s", to_email, exc)
        return False


def notify_new_question(question):
    if not _notifications_enabled():
        return

    recipients = User.objects.select_related('profile').filter(
        is_active=True,
        profile__notify_new_posts=True,
    ).exclude(
        pk=question.author_id,
    ).exclude(
        email='',
    )

    url = _question_url(question)
    subject = f"New post on Philosofriends: {question.title[:120]}"
    for recipient in recipients:
        body = (
            f"{question.author.username} published a new post:\n\n"
            f"{question.title}\n\n"
            f"Read it here: {url}\n"
        )
        _send_smtp2go_email(recipient.email, subject, body)


def notify_new_comment(comment):
    if not _notifications_enabled():
        return

    question = comment.question
    recipients = {}

    if comment.parent_id:
        parent_author = comment.parent.author
        if (
            parent_author_id := parent_author.pk
        ) != comment.author_id and parent_author.profile.notify_replies_to_comments and parent_author.email:
            recipients[parent_author_id] = {
                'email': parent_author.email,
                'username': parent_author.username,
                'reasons': {'comment'},
            }

    post_author = question.author
    if (
        post_author_id := post_author.pk
    ) != comment.author_id and post_author.profile.notify_replies_to_posts and post_author.email:
        recipient = recipients.get(
            post_author_id,
            {
                'email': post_author.email,
                'username': post_author.username,
                'reasons': set(),
            },
        )
        recipient['reasons'].add('post')
        recipients[post_author_id] = recipient

    if not recipients:
        return

    url = _question_url(question)
    for recipient in recipients.values():
        reasons = recipient['reasons']
        if reasons == {'comment'}:
            reason_text = "a reply to your comment"
        elif reasons == {'post'}:
            reason_text = "a reply to your post"
        else:
            reason_text = "activity on your post and comment"
        subject = f"New reply on Philosofriends: {question.title[:120]}"
        body = (
            f"You have {reason_text}.\n\n"
            f"{comment.author.username} wrote:\n"
            f"{comment.body[:800]}\n\n"
            f"Read it here: {url}\n"
        )
        _send_smtp2go_email(recipient['email'], subject, body)
