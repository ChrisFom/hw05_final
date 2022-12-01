# forms.py
from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': ('Текст поста'),
            'group': ('Название группы')
        }
        help_texts = {
            'text': ('Напишите свою информацию'),
            'group': ('Напишите название группы')
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': ('Текст комментария'),
        }
        help_texts = {
            'text': ('Напишите свой комментарий'),
        }
