from django import template
from django.urls import resolve
register = template.Library()

@register.simple_tag(takes_context=True)
def active_link(context, url_name):
    """
    Returns active classes if current request matches the url_name.
    Usage: {% active_link 'dashboard' %}
    """
    request = context.get('request')
    if not request:
        return ''
    try:
        current_url_name = resolve(request.path_info).url_name
    except:
        current_url_name = None

    if current_url_name == url_name:
        return 'font-semibold text-red-700 bg-red-50 border-l-4 border-red-600 shadow-sm'
    return 'text-gray-700 hover:bg-red-50 hover:text-red-700 transition'