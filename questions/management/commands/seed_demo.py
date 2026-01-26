import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from questions.models import Comment, Question


class Command(BaseCommand):
    help = "Seed demo questions and comments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo users/questions/comments before seeding.",
        )

    def handle(self, *args, **options):
        random.seed(42)

        if options["reset"]:
            Comment.objects.filter(author__username__startswith="demo_").delete()
            Question.objects.filter(author__username__startswith="demo_").delete()
            User.objects.filter(username__startswith="demo_").delete()

        usernames = [
            "demo_aletheia",
            "demo_socrates",
            "demo_zeno",
            "demo_hypatia",
            "demo_epictetus",
            "demo_heraclitus",
            "demo_ava",
            "demo_mira",
            "demo_noah",
            "demo_kai",
            "demo_lina",
            "demo_oren",
        ]

        users = []
        for username in usernames:
            user, _ = User.objects.get_or_create(username=username)
            users.append(user)

        questions = [
            "Is a meaningful life possible without a narrative?",
            "If memory defines identity, who are we after forgetting?",
            "Can an action be truly altruistic if it feels good?",
            "Does suffering have intrinsic value, or only instrumental?",
            "Is love a choice or a discovery?",
            "Do we owe anything to future people who do not exist yet?",
            "What does it mean to forgive someone who has not changed?",
            "Is beauty objective or just shared agreement?",
            "Can technology deepen wisdom, or only knowledge?",
            "Is there a moral difference between omission and commission?",
            "Are we morally responsible for our implicit biases?",
            "Does free will require alternative possibilities?",
            "Can a life be good if it is not happy?",
            "Is it rational to fear death?",
            "What is the ethical limit of self-improvement?",
            "Are we the same person over time or a series of selves?",
            "Can we be courageous without feeling fear?",
            "Is there a duty to understand those we disagree with?",
            "Does art need to be understood to be valuable?",
            "Is authenticity compatible with social roles?",
            "Does consciousness require language?",
            "Can traditions be justified without original reasons?",
            "Is it possible to respect someone while rejecting their worldview?",
            "Do animals have rights or only welfare?",
            "Is there a moral obligation to be optimistic?",
            "Is silence a form of complicity?",
            "Can we be friends with someone we morally condemn?",
            "Is moral progress real or just changing tastes?",
            "Does the universe owe us meaning?",
            "Is solitude a virtue or a retreat?",
        ]

        bodies = [
            "I keep circling this when thinking about personal projects.",
            "Curious how this changes if we shift cultures or generations.",
            "What thinkers wrestle with this most directly?",
            "Looking for arguments on both sides.",
            "Is there a practical way to live with this tension?",
            "Wondering if this is just a verbal puzzle.",
            "I have a hunch, but it feels incomplete.",
            "Does this hinge on a hidden assumption?",
        ]

        comment_snippets = [
            "I lean yes, but only if we separate motives from outcomes.",
            "This reminds me of a paradox about identity and memory.",
            "Maybe we should ask what problem the question solves.",
            "It depends on whether we treat meaning as constructed or discovered.",
            "I would frame this in terms of responsibility rather than intention.",
            "There is a quiet dignity in ambiguity here.",
            "I see a tension between authenticity and social obligation.",
            "The answer shifts if we zoom out to a communal perspective.",
            "I worry this assumes too much about stable selves.",
            "If we swap in another value, the conclusion flips.",
            "Some traditions answer this, but I'm not sure we should accept them.",
            "This seems like a case for humility rather than certainty.",
            "I think it is less about truth and more about how we live.",
            "Consider the costs of getting this wrong.",
            "Maybe the question is a symptom, not the root.",
        ]

        reply_snippets = [
            "I see the point, but the distinction might be doing too much work.",
            "This pushes me to clarify what I mean by identity here.",
            "Interesting — how would this change in a collective setting?",
            "Could be, though it risks turning the question into a tautology.",
            "I like this framing; it makes the trade-offs more explicit.",
            "Yes, and it also depends on what counts as a reason in the first place.",
            "I think this is right, but only if we allow for uncertainty.",
            "This feels like a good place to bring in examples.",
        ]

        created_questions = 0
        for title in questions:
            author = random.choice(users)
            body = random.choice(bodies) if random.random() < 0.7 else ""
            question = Question.objects.create(title=title, body=body, author=author)
            created_questions += 1

            comment_pool = []
            for _ in range(random.randint(2, 5)):
                comment_author = random.choice(users)
                comment = Comment.objects.create(
                    question=question,
                    author=comment_author,
                    body=random.choice(comment_snippets),
                    created_at=timezone.now(),
                )
                comment_pool.append(comment)

            reply_count = random.randint(1, 4)
            for _ in range(reply_count):
                parent = random.choice(comment_pool)
                reply_author = random.choice(users)
                Comment.objects.create(
                    question=question,
                    parent=parent,
                    author=reply_author,
                    body=random.choice(reply_snippets),
                    created_at=timezone.now(),
                )

        self.stdout.write(self.style.SUCCESS(f"Seeded {created_questions} questions."))
