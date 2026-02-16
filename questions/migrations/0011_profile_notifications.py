from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0010_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='notify_new_posts',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_replies_to_comments',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_replies_to_posts',
            field=models.BooleanField(default=False),
        ),
    ]
