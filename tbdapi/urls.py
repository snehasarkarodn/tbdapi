from django.contrib import admin
from django.urls import include, path
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path('open_ai_tbd_gen/', include('open_ai_tbd_gen.urls'))
]
