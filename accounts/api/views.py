from accounts.api.serializers import (
    LoginSerializer,
    SignupSerializer,
    UserProfileSerializerForUpdate,
    UserSerializer,
    UserSerializerWithProfile,
)
from accounts.models import UserProfile
from django.contrib.auth.models import User
from django.contrib.auth import (
    login as django_login,
    logout as django_logout,
    authenticate as django_authenticate,
)
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.permissions import IsObjectOwner
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializerWithProfile
    permission_classes = (permissions.IsAdminUser,)


class AccountViewSet(viewsets.ViewSet):
    serializer_class = SignupSerializer

    @action(methods=['GET'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='GET', block=True))
    # accounts是主资源目录，下面的次目录可以自定义为action
    # detail指url后面不需要id，它不是定义在某个object上的动作，而是定义在整体资源上的动作
    def login_status(self, request):
        data = {
            'has_logged_in': request.user.is_authenticated,
            'ip': request.META['REMOTE_ADDR'],
        }
        if request.user.is_authenticated:
            data['user'] = UserSerializer(request.user).data
        return Response(data)

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def logout(self, request):
        django_logout(request)
        return Response({'success': True})

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def login(self, request):
        # get username and password from request, convert them to serializer
        serializer = LoginSerializer(data=request.data)  # POST用request.data获取参数
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=400)

        # validation ok, login
        username = serializer.validated_data['username'].lower()
        password = serializer.validated_data['password'].lower()

        # authenticate user之后才能login
        user = django_authenticate(username=username, password=password)
        if not user or user.is_anonymous:
            return Response({
                "success": False,
                "message": "Username and password does not match.",
            }, status=400)

        # login
        django_login(request, user)
        return Response({
            "success": True,
            "user": UserSerializer(user).data,
        })

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=400)

        user = serializer.save()  # serializer.save()会调用serializer.create()方法
        django_login(request, user)
        return Response({
            'success': True,
            'user': UserSerializer(user).data,
        }, status=201)


class UserProfileViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.UpdateModelMixin,
):
    queryset = UserProfile
    permission_classes = (permissions.IsAuthenticated, IsObjectOwner)
    serializer_class = UserProfileSerializerForUpdate

