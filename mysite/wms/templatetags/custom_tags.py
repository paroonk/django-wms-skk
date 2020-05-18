import re

from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.filter(name='k')
def key(d, k):
    """
    Return dictionary value with key
    """
    return d[k]


@register.simple_tag(takes_context=True)
def active(context, pattern_or_url):
    try:
        pattern = '^' + reverse(pattern_or_url)
    except NoReverseMatch:
        pattern = pattern_or_url
    path = context['request'].path
    if re.search(pattern, path):
        return 'active'
    return ''


@register.simple_tag(takes_context=True)
def menu_open(context, pattern_or_url):
    try:
        pattern = '^' + reverse(pattern_or_url)
    except NoReverseMatch:
        pattern = pattern_or_url
    path = context['request'].path
    if re.search(pattern, path):
        return 'menu-open'
    return ''


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Return encoded URL parameters that are the same as the current
    request's parameters, only with the specified GET parameters added or changed.
    """
    d = context['request'].GET.copy()
    for k, v in kwargs.items():
        d[k] = v
    for k in [k for k, v in d.items() if not v]:
        del d[k]
    return d.urlencode()


@register.filter
def get_fields(instance):
    """
    Returns field name for a model.
    """
    return [field.name for field in instance._meta.fields]


@register.simple_tag
def get_verbose_name(instance, field_name):
    """
    Returns verbose_name for a field.
    """
    return instance._meta.get_field(field_name).verbose_name.title()
