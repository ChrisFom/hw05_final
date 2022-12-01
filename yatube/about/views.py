# Create your views here.
from django.views.generic.base import TemplateView


class AboutAuthorView(TemplateView):
    template_name = 'about/author.html'


# Описать класс AboutTechView для страницы about/tech
class AboutTechView(TemplateView):

    template_name = 'about/tech.html'
