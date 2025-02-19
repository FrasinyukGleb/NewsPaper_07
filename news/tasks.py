import datetime

from celery import shared_task

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

from .models import Post, Category, PostCategory

import logging
logger = logging.getLogger(__name__)

@shared_task
def send_post_notification(pk):
    post = Post.objects.get(pk=pk)
    categories = post.category.all()
    subscribers_emails = []

    for cat in categories:
        subscribers = cat.subscribers.all()
        subscribers_emails += [s.email for s in subscribers]

    subscribers_emails = set(subscribers_emails)

    html_content = render_to_string(
        'post_created_celery.html',
        {
            'text': post.preview,
            'link': f'http://127.0.0.1:8000/news/{pk}',

        }
    )

    msg = EmailMultiAlternatives(
        subject=post.title,
        body='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=subscribers_emails,
    )

    msg.attach_alternative(html_content, 'text/html')
    msg.send()



@shared_task
def send_weekly_newsletter():
    last_week = datetime.timezone.now() - datetime.timedelta(days=7)  # определяем дату неделей ранее текущей
    posts = Post.objects.filter(date_add__gte=last_week)  # получаем посты за последнюю неделю
    categories = set(
        post.category.values_list('name', flat=True) for post in posts)  # получаем имена категорий постов за неделю
    users = set(
        User.objects.filter(categories__name__in=categories))  # получаем всех подписчиков на категории постов за неделю

    for user in users:  # проходимся циклом по всем подписчикам
        sub_cat = user.categories.values_list('name', flat=True)  # получаем имена категорий текущего подписчика
        posts_cat_sub = posts.filter(
            category__name__in=sub_cat)  # фильтруем список постов за неделю по категориям текущего подписчика

        from_email = settings.DEFAULT_FROM_EMAIL  # получаем почту отправления
        subject = 'Еженедельная рассылка'  # формируем заголовок письма
        message = f"Привет, {user.username}!\n\nНовые посты за неделю:\n\n"  # формируем содержание письма
        for post in posts_cat_sub:  # формируем список постов за неделю в категориях текущего подписчика
            message += f"{post.post_title}\n"  # добавляем в содержание письма заголовок текущего поста из списка
            message += f"URL: http://127.0.0.1:8000{post.get_absolute_url()}\n"  # добавляем в содержание письма ссылку на текущий пост из списка

        send_mail(subject, message, from_email, [user.email])  # отправляем письмо