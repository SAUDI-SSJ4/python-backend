# CRUD package
from .base import CRUDBase
from .student import student
from .template import template
from .faq import faq
from .opinion import opinion
from .about import about
from .slider import slider
from .settings import settings
from .academy_content import academy_content

__all__ = [
    "CRUDBase",
    "student",
    "template", 
    "faq",
    "opinion",
    "about",
    "slider",
    "settings",
    "academy_content"
] 