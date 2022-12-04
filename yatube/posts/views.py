from django.shortcuts import render, get_object_or_404
from .models import Post, Group, User, Follow
from django.core.paginator import Paginator
from django.shortcuts import redirect
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

NUM_POSTS = 10


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.select_related('author', 'group')
    paginator = Paginator(post_list, NUM_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    paginator = Paginator(posts, NUM_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'group': group,
               'page_obj': page_obj, }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    following = (request.user.is_authenticated
                 and request.user.follower.filter(author=author).exists()
                 )
    posts = author.posts.select_related('author')
    count = author.posts.count()
    paginator = Paginator(posts, NUM_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'author': author,
        'count': count,
        'page_obj': page_obj,
        'following': following,
    }
    template = 'posts/profile.html'
    return render(request, template, context)


def post_detail(request, post_id):
    # Здесь код запроса к модели и создание словаря контекста
    post = get_object_or_404(Post, id=post_id)
    posts_author = post.author
    posts_count = Post.objects.filter(author=posts_author).count()
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('posts:post_detail', post_id=post_id)
    form = CommentForm()
    context = {
        'posts_count': posts_count,
        'post': post,
        'form': form,
        'comments': post.comments.all(),
    }

    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            post = form.save(False)
            post.author = request.user
            form.save()
            return redirect('posts:profile', request.user)
    form = PostForm()
    context = {'form': form}
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)

    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    # Получите пост и сохраните его в переменную post.
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, NUM_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', author)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    is_follower = Follow.objects.filter(user=request.user, author=author)
    if is_follower.exists():
        is_follower.delete()
    return redirect('posts:profile', username=author)
