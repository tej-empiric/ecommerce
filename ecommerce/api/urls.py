from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from django.conf.urls.static import static
from django.conf import settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# to generate documentation
schema_view = get_schema_view(
    openapi.Info(
        title="E-commerce API",
        default_version="v1",
        description="API for an e-commerce website",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


router = DefaultRouter()
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemViewSet, basename="cart-items")


urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("admin/users/", UserView.as_view(), name="users"),
    path("products/", ProductList.as_view()),
    path("products/<int:pk>/", ProductDetail.as_view()),
    path("categories/", CategoryList.as_view()),
    path("categories/<int:pk>/", CategoryDetail.as_view()),
    path("orders/create/", CreateOrderView.as_view(), name="order-create"),
    path("orders/", ListOrderView.as_view(), name="order-list"),
    path(
        "orders/<int:pk>/",
        OrderRetrieveUpdateDestroyAPIView.as_view(),
        name="order-detail",
    ),
    path("reviews/", ReviewCreateView.as_view(), name="create-review"),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),  # for documentation
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
