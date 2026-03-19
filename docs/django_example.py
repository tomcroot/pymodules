"""
Example: Full Django project using pymodules.

Project layout:

    myproject/
    ├── manage.py
    ├── myproject/
    │   ├── settings.py      ← this file's patterns
    │   └── urls.py
    └── modules/
        ├── Blog/
        └── Shop/

Run:
    pymodules make Blog
    pymodules make Shop
    python manage.py migrate
    python manage.py runserver
"""

# ─────────────────────────────────────────────
# myproject/settings.py
# ─────────────────────────────────────────────
from pathlib import Path
from pymodules.integrations.django import DjangoModuleRegistry

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-replace-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# 1. Create the registry — scans BASE_DIR/modules automatically
MODULE_REGISTRY = DjangoModuleRegistry(modules_path=BASE_DIR / "modules")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 2. Auto-register all enabled modules
    *MODULE_REGISTRY.installed_apps(),
]

# 3. Point Django to each module's own migrations folder
MIGRATION_MODULES = MODULE_REGISTRY.migration_modules()

# 4. Merge UPPER_CASE vars from every module's config/config.py
locals().update(MODULE_REGISTRY.collect_settings())

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"
STATIC_URL = "/static/"


# ─────────────────────────────────────────────
# myproject/urls.py
# ─────────────────────────────────────────────
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),

    # 5. Auto-include every enabled module's urlpatterns
    *settings.MODULE_REGISTRY.url_patterns(),
]
"""


# ─────────────────────────────────────────────
# modules/Blog/apps.py
# ─────────────────────────────────────────────
"""
from django.apps import AppConfig

class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.Blog"
    label = "blog"
"""


# ─────────────────────────────────────────────
# modules/Blog/routes.py
# ─────────────────────────────────────────────
"""
from django.urls import path
from .views import post_list, post_detail

prefix = "blog"   # accessible at /blog/

urlpatterns = [
    path("", post_list, name="blog-list"),
    path("<int:pk>/", post_detail, name="blog-detail"),
]
"""


# ─────────────────────────────────────────────
# modules/Blog/config/config.py
# ─────────────────────────────────────────────
"""
# These are merged into Django settings automatically
BLOG_POSTS_PER_PAGE = 10
BLOG_ALLOW_COMMENTS = True
BLOG_CACHE_TTL = 300
"""


# ─────────────────────────────────────────────
# modules/Blog/providers.py
# ─────────────────────────────────────────────
"""
from pymodules import ServiceProvider

class BlogServiceProvider(ServiceProvider):
    def register(self) -> None:
        # Connect Django signals, register middleware, etc.
        pass

    def boot(self) -> None:
        pass
"""
