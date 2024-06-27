from django.shortcuts import render
from rest_framework import generics
from .models import *
from .serializers import *
from rest_framework import status, viewsets, permissions, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .service import Cart
from django_filters import rest_framework as filters


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"user": serializer.data}, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class UserView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser == True:
            return CustomUser.objects.all().order_by("id")
        else:
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__name", lookup_expr="icontains")

    class Meta:
        model = Product
        fields = ["category", "price"]


class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["category", "price"]
    search_fields = ["name", "description"]


class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser == True:
            return Category.objects.all()
        else:
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

       
class CartAPI(APIView):

    def get(self, request, format=None):
        cart = Cart(request)

        return Response(
            {"data": list(cart.__iter__()), "cart_total_price": cart.get_total_price()},
            status=status.HTTP_200_OK,
        )

    def post(self, request, **kwargs):
        cart = Cart(request)

        if "remove" in request.data:
            product = request.data["product"]
            cart.remove(product)

        elif "clear" in request.data:
            cart.clear()

        else:
            product = request.data
            cart.add(
                product=product["product"],
                quantity=product["quantity"],
                overide_quantity=(
                    product["overide_quantity"]
                    if "overide_quantity" in product
                    else False
                ),
            )

        return Response({"message": "cart updated"}, status=status.HTTP_202_ACCEPTED)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
