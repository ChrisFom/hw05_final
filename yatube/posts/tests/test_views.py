from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from ..models import Post, Group, User, Follow


class PostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Petr')
        # Создадим запись в БД
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )

        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug2',
            description='Тестовое описание2',
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
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )

    def setUp(self):
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_post_content(self, post):
        self.assertEqual(post.author.username, self.post.author.username)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        # проверка контекста на картинку
        self.assertEqual(post.image, self.post.image)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                cache.clear()
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_content(self):
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_post_content(first_object)

    def test_profile_show_correct_content(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(response.context.get('author'), self.user)
        self.assertEqual(response.context.get('count'), 1)
        first_object = response.context['page_obj'][0]
        self.check_post_content(first_object)

    def test_group_list_show_correct_content(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(response.context.get('group'), self.group)
        first_object = response.context['page_obj'][0]
        self.check_post_content(first_object)

    # Проверка словаря контекста страницы create (в нём передаётся форма)
    def test_post_create_show_correct_context(self):

        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.CharField,
            'group': forms.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.CharField,
            'group': forms.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('is_edit'), True)

    def test_post_detail_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        context_post = response.context.get('post')
        self.check_post_content(context_post)
        self.assertEqual(response.context.get('posts_count'), 1)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_created_post_appears_on_related_pages(self):

        response_group_post = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(len(response_group_post.context.get('page_obj')), 1)
        response_index = self.authorized_client.get(reverse('posts:index'))
        first_object = response_index.context['page_obj'][0]
        self.assertEqual(first_object.id, 1)

    def test_created_post_not_appears_in_another_group(self):
        response_not_group_post = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group2.slug}))
        self.assertEqual(len(response_not_group_post.context.
                             get('page_obj')), 0)

    def test_response_cache_correct(self):
        Post.objects.create(author=self.user,
                            text='Тестовый пост',
                            group=self.group)
        response = self.authorized_client.get(reverse('posts:index'))
        not_delete = response.content
        Post.objects.get(id=1).delete()
        response = self.authorized_client.get(reverse('posts:index'))
        after_delete = response.content
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        after_cache_clear = response.content
        self.assertEqual(not_delete, after_delete)
        self.assertNotEqual(after_delete, after_cache_clear)


class PaginatorViewsTest1(TestCase):
    NUM_POSTS_FIRST_PAGE = 10
    NUM_POSTS_SECOND_PAGE = 3
    NUM_POSTS_ALL = 13

    def setUp(self):
        self.unauthorized_client = Client()
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа!',
                                          slug='test_group')
        text_post = [Post(
            author=self.user,
            group=self.group,
            text='Тестовый текст' + str(i))
            for i in range(self.NUM_POSTS_ALL)]
        self.post = Post.objects.bulk_create(text_post)

    def test_correct_page_context_unauthorized_client(self):
        '''Проверка количества постов на первой и второй страницах. '''

        tests_pages = [(self.NUM_POSTS_FIRST_PAGE, 1),
                       (self.NUM_POSTS_SECOND_PAGE, 2)]
        for posts_on_page, page_number in tests_pages:
            pages = (
                reverse('posts:index'),
                reverse('posts:profile',
                        kwargs={'username': self.user.username}),
                reverse('posts:group_list',
                        kwargs={'slug': self.group.slug})
            )
            for page in pages:
                cache.clear()
                with self.subTest(page=page):
                    response = self.unauthorized_client.\
                        get(page, {'page': page_number})
                    count = len(response.context['page_obj'])
                    error_name = (f'Ошибка: {count} постов,'
                                  f' должно {posts_on_page}')
                    self.assertEqual(
                        count,
                        posts_on_page,
                        error_name)
                    first_object = response.context['page_obj'][0]
                    post_author_0 = first_object.author.username
                    post_group_0 = first_object.group.title
                    self.assertEqual(post_author_0, 'auth')
                    self.assertEqual(post_group_0, 'Тестовая группа!')


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = User.objects.create_user(username="test-author")
        cls.follower = User.objects.create_user(username='follower')
        cls.not_follower = User.objects.create_user(username='not_follower')

    def setUp(self) -> None:
        self.test_user_client = Client()
        self.test_user_client.force_login(FollowTests.test_user)
        self.follower_client = Client()
        self.follower_client.force_login(FollowTests.follower)
        self.not_follower_client = Client()
        self.not_follower_client.force_login(FollowTests.not_follower)

    def test_follow_index_show_correct_post(self):
        """Новая запись пользователя появляется в ленте тех, кто
        на него подписан и не появляется в ленте тех, кто не подписан."""
        Follow.objects.create(
            author=self.test_user,
            user=self.follower
        )
        Post.objects.create(
            text='test_one_post',
            author=self.test_user
        )
        response_not_follower = self.not_follower_client. \
            get(reverse('posts:follow_index'))
        before_not_follower = len(response_not_follower.context["page_obj"])
        response_follower = self.follower_client. \
            get(reverse('posts:follow_index'))
        before_follower = len(response_follower.context["page_obj"])
        Post.objects.create(
            text='test_one_post',
            author=self.test_user)
        after_not_follower = len(response_not_follower.context["page_obj"])
        self.assertEqual(before_not_follower, after_not_follower)
        after_follower = len(response_follower.context["page_obj"])
        self.assertEqual(before_follower, after_follower)
