# courses/templatetags/video_tags.py
from django import template
import re

register = template.Library()

@register.filter
def youtube_embed_url(url):
    """Convert YouTube URL to embed URL"""
    if not url:
        return ""

    # Handle youtu.be links
    url = re.sub(r'https?://youtu\.be/([^\?]+)', r'https://www.youtube.com/embed/\1', url)
    
    # Handle youtube.com/watch?v= links
    url = re.sub(r'https?://(?:www\.)?youtube\.com/watch\?v=([^\?&]+)', r'https://www.youtube.com/embed/\1', url)
    
    return url