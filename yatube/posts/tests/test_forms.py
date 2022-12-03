import shutil
import tempfile

from ..models import Post, Group, User, Comment
from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from http import HTTPStatus
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Buggy_NaMe')
        cls.group = Group.objects.create(
            title='Баг группа',
            slug='Bug-slug',
            description='Тестовое описание',
        )

        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        cls.uploaded = SimpleUploadedFile(
            name='posts/small.gif',
            content=cls.small_gif,
            content_type='iamge/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        post_count = Post.objects.count()

        form_data = {
            'text': 'тест',
            'group': PostFormTests.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post = Post.objects.first()
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse('posts:profile', kwargs={'username': self.user})
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group_id, form_data['group'])
        self.assertTrue(
            Post.objects.filter(
                text=post.text,
                image='posts/' + form_data['image'].name
            ).exists())

    def test_edit_post(self):
        """Проверка редактирования записи авторизированным клиентом."""
        post = Post.objects.create(
            text="Текст поста для редактирования",
            author=self.user,
            group=self.group,
        )

        form_data = {
            "text": "Отредактированный текст поста",
            "group": self.group.id,
        }
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=[post.id]),
            data=form_data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse("posts:post_detail", kwargs={"post_id": post.id})
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.latest("id")
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(post.group_id, form_data["group"])

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        post = Post.objects.create(
            text="Текст поста для редактирования",
            author=self.user,
            group=self.group,
        )
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        self.authorized_client.post(
            reverse('posts:add_comment', args=(post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        comment1 = Comment.objects.first()
        self.assertEqual(
            comment1.text, form_data['text']
        )
