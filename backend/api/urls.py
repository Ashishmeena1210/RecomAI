from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),
    path("domains/", views.DomainListView.as_view()),
    path("domains/<str:domain>/schema/", views.SchemaView.as_view()),
    path("domains/<str:domain>/search/", views.SearchView.as_view()),
    path("domains/<str:domain>/recommend/", views.RecommendView.as_view()),
]