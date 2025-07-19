from django import template

register = template.Library()

@register.filter
def split_tags(tags_string):
    """Splits a comma-separated string of tags into a list."""
    if tags_string:
        return [tag.strip() for tag in tags_string.split(',') if tag.strip()]
    return []