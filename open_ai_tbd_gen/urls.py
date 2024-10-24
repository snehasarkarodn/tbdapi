from django.urls import path
from tbd_gen import attribute_fetch 

urlpatterns = [
    path('attribute_fetch', attribute_fetch, name='attribute_fetch'), 
]