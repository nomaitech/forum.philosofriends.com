from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from unittest.mock import patch

from .models import Comment, Question


class AdminImpersonationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin-pass-1234',
            is_superuser=True,
            is_staff=True,
        )
        self.target = User.objects.create_user(
            username='target',
            email='target@example.com',
            password='target-pass-1234',
        )
        self.other = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='other-pass-1234',
        )
        self.question = Question.objects.create(
            title='Existing question',
            body='Context',
            author=self.other,
        )

    def test_admin_can_impersonate_for_question_submission(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('impersonate_start'), {'user_id': self.target.id})

        response = self.client.post(
            reverse('question_create'),
            {'post_type': 'question', 'title': 'Impersonated post', 'body': 'Hello'},
        )

        self.assertEqual(response.status_code, 302)
        created = Question.objects.get(title='Impersonated post')
        self.assertEqual(created.author, self.target)

    def test_admin_can_impersonate_for_comment_submission(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('impersonate_start'), {'user_id': self.target.id})

        response = self.client.post(
            reverse('question_detail_slug', args=[self.question.slug]),
            {'body': 'Impersonated comment'},
        )

        self.assertEqual(response.status_code, 302)
        comment = Comment.objects.get(body='Impersonated comment')
        self.assertEqual(comment.author, self.target)
        self.assertEqual(comment.question, self.question)

    def test_non_admin_cannot_start_impersonation(self):
        self.client.force_login(self.other)
        self.client.post(reverse('impersonate_start'), {'user_id': self.target.id})

        response = self.client.post(
            reverse('question_create'),
            {'post_type': 'question', 'title': 'Normal post', 'body': 'No impersonation'},
        )

        self.assertEqual(response.status_code, 302)
        created = Question.objects.get(title='Normal post')
        self.assertEqual(created.author, self.other)

    def test_admin_can_stop_impersonation(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('impersonate_start'), {'user_id': self.target.id})
        self.client.post(reverse('impersonate_stop'))

        response = self.client.post(
            reverse('question_create'),
            {'post_type': 'question', 'title': 'Admin post', 'body': 'After stop'},
        )

        self.assertEqual(response.status_code, 302)
        created = Question.objects.get(title='Admin post')
        self.assertEqual(created.author, self.admin)


class ProfileSettingsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='owner-pass-1234',
        )
        self.other = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='other-pass-1234',
        )

    def test_nav_username_links_to_own_profile(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('question_list'))
        self.assertContains(
            response,
            f'href="{reverse("profile_detail", args=[self.owner.username])}"',
            html=False,
        )

    def test_owner_can_update_email_and_notification_settings(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('profile_detail', args=[self.owner.username]),
            {
                'email': 'new-owner@example.com',
                'notify_new_posts': 'on',
                'notify_replies_to_posts': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.owner.profile.refresh_from_db()
        self.assertEqual(self.owner.email, 'new-owner@example.com')
        self.assertTrue(self.owner.profile.notify_new_posts)
        self.assertFalse(self.owner.profile.notify_replies_to_comments)
        self.assertTrue(self.owner.profile.notify_replies_to_posts)

    def test_non_owner_cannot_update_profile_settings(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse('profile_detail', args=[self.owner.username]),
            {
                'email': 'hijack@example.com',
                'notify_new_posts': 'on',
                'notify_replies_to_comments': 'on',
                'notify_replies_to_posts': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.owner.profile.refresh_from_db()
        self.assertEqual(self.owner.email, 'owner@example.com')
        self.assertFalse(self.owner.profile.notify_new_posts)
        self.assertFalse(self.owner.profile.notify_replies_to_comments)
        self.assertFalse(self.owner.profile.notify_replies_to_posts)


@override_settings(
    EMAIL_NOTIFICATIONS_ENABLED=True,
    SMTP2GO_API_KEY='test-api-key',
    SMTP2GO_FROM_EMAIL='noreply@philosofriends.com',
    SITE_URL='https://forum.philosofriends.com',
)
class NotificationDispatchTests(TestCase):
    @patch('questions.notifications._send_smtp2go_email')
    def test_new_post_notifies_opted_in_users(self, mock_send):
        author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='author-pass-1234',
        )
        watcher = User.objects.create_user(
            username='watcher',
            email='watcher@example.com',
            password='watcher-pass-1234',
        )
        watcher.profile.notify_new_posts = True
        watcher.profile.save(update_fields=['notify_new_posts'])

        Question.objects.create(
            title='A fresh post',
            body='Body',
            author=author,
        )

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[0][0], 'watcher@example.com')

    @patch('questions.notifications._send_smtp2go_email')
    def test_reply_notifies_comment_and_post_authors(self, mock_send):
        post_author = User.objects.create_user(
            username='post_author',
            email='post_author@example.com',
            password='post-author-pass-1234',
        )
        comment_author = User.objects.create_user(
            username='comment_author',
            email='comment_author@example.com',
            password='comment-author-pass-1234',
        )
        replier = User.objects.create_user(
            username='replier',
            email='replier@example.com',
            password='replier-pass-1234',
        )
        post_author.profile.notify_replies_to_posts = True
        post_author.profile.save(update_fields=['notify_replies_to_posts'])
        comment_author.profile.notify_replies_to_comments = True
        comment_author.profile.save(update_fields=['notify_replies_to_comments'])

        question = Question.objects.create(
            title='Original post',
            body='Body',
            author=post_author,
        )
        parent = Comment.objects.create(
            question=question,
            author=comment_author,
            body='Parent comment',
        )

        Comment.objects.create(
            question=question,
            parent=parent,
            author=replier,
            body='Reply comment',
        )

        recipients = {call[0][0] for call in mock_send.call_args_list}
        self.assertEqual(recipients, {'post_author@example.com', 'comment_author@example.com'})
        self.assertEqual(mock_send.call_count, 2)

    @patch('questions.notifications._send_smtp2go_email')
    def test_reply_deduplicates_when_same_user_subscribes_to_both(self, mock_send):
        owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='owner-pass-1234',
        )
        replier = User.objects.create_user(
            username='replier',
            email='replier@example.com',
            password='replier-pass-1234',
        )
        owner.profile.notify_replies_to_posts = True
        owner.profile.notify_replies_to_comments = True
        owner.profile.save(update_fields=['notify_replies_to_posts', 'notify_replies_to_comments'])

        question = Question.objects.create(
            title='Owner post',
            body='Body',
            author=owner,
        )
        parent = Comment.objects.create(
            question=question,
            author=owner,
            body='Owner comment',
        )

        Comment.objects.create(
            question=question,
            parent=parent,
            author=replier,
            body='Reply to owner',
        )

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[0][0], 'owner@example.com')
