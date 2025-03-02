from rest_framework.response import Response
from rest_framework import generics
from django_filters import rest_framework as filters
from rest_framework import status, viewsets, permissions, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import *
from .serializers import *
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework import views
from rest_framework.parsers import JSONParser
from django.http import HttpResponse, JsonResponse


class IsAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_staff


class IsAdminOrOrderOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True

        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user

        if request.method == "PATCH":
            return (
                obj.user == request.user and request.data.get("status") == "Cancelled"
            )

        return False


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
            refreshToken = RefreshToken(refresh_token)
            refreshToken.blacklist()

            return Response(
                {"Log out successfull."}, status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            return Response(
                {f"Error in Log out. {str(e)}, {status.HTTP_400_BAD_REQUEST}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser == True:
            return CustomUser.objects.all().order_by("email")
        else:
            raise PermissionDenied("You do not have permission to perform this action.")


class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by("id")
    serializer_class = CategoryListSerializer
    permission_classes = [IsAdminOrReadOnly]


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__name", lookup_expr="icontains")

    class Meta:
        model = Product
        fields = ["category", "price"]


class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminOrReadOnly]


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product")

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = Cart.objects.create(user=request.user)

        try:
            product = Product.objects.get(pk=product_id)

        except Product.DoesNotExist:
            return Response({"error": "Product does not exist"})

        if product.is_available == False:
            return Response({"error": "Product is out of stock"})

        cart_item = CartItem.objects.create(cart=cart, product=product)

        serializer = self.get_serializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_quantity = request.data.get("quantity")

        if new_quantity is not None:
            try:
                new_quantity = int(new_quantity)
                if new_quantity <= 0:
                    return Response(
                        {"error": "Quantity must be a positive integer"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except ValueError:
                return Response(
                    {"error": "Quantity must be an integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if instance.product.quantity < new_quantity:
                return Response(
                    {"error": "Not enough quantity available"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.quantity = new_quantity
            instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class CreateOrderView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        cart_items = CartItem.objects.filter(cart=user.cart)

        if not cart_items.exists():
            return Response(
                {"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        order_data = {
            "user": user.id,
            "items": [
                {
                    "product": item.product.id,
                    "quantity": item.quantity,
                    "price": item.product.price,
                }
                for item in cart_items
            ],
        }

        for item in cart_items:
            product = item.product
            if item.quantity > product.quantity:
                return Response(
                    {"error": f"Not enough {product.name} available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # create order
        serializer = self.get_serializer(data=order_data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        # update product quantity
        for item in cart_items:
            product = item.product
            product.quantity -= item.quantity
            product.save()

        cart_items.delete()

        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class ListOrderView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().order_by("-created_at")
        else:
            return Order.objects.filter(user=self.request.user).order_by("-created_at")


class OrderRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminOrOrderOwner]


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):

        user = self.request.user
        product_id = self.request.data.get("product")
        rating = self.request.data.get("rating")

        if rating is None or not (1 <= int(rating) <= 5):
            raise ValidationError("Rating must be between 1 to 5.")

        try:
            product = (
                OrderItem.objects.filter(
                    order__user=user, order__status="Delivered", product_id=product_id
                )
                .first()
                .product
            )

        except OrderItem.DoesNotExist:
            raise ValidationError(
                "You can only review products that have been delivered."
            )

        if Review.objects.filter(user=user, product=product).exists():
            raise ValidationError("You have already reviewed this product.")

        serializer.save(user=user, product=product)


class WalletDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = Wallet.objects.get(user=request.user)
        serializer = WalletSerializer(wallet)
        return JsonResponse(serializer.data, status=200)


class ReferralView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = ReferralCode.objects.get(user=request.user)
        serializer = ReferralCodeSerializer(code)
        return JsonResponse(serializer.data, status=200)

    def post(self, request):
        data = request.data
        serializer = ReferralCodeSerializer(data=data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "msg": f"Referral code sent to {serializer.validated_data.get('to_email')}"
                },
                status=202,
            )
        return Response(serializer.errors, status=400)
