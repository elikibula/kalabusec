# news/templatetags/news_filters.py
from django import template
from news.models import News
import os

register = template.Library()

@register.filter
def is_article(post):
    return isinstance(post, News)

@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter
def basename(value):
    """
    Return the final component of a path (filename).
    Usage in template: {{ some_path|basename }}
    """
    try:
        return os.path.basename(value)
    except Exception:
        return value

@register.filter
def split(value, delimiter=','):
    """
    Optional: behave like Python's split() if you still want split available.
    Returns a list (templates can iterate over it).
    Usage: {{ some_string|split:"," }}
    """
    try:
        return value.split(delimiter)
    except Exception:
        return []
    

@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})



