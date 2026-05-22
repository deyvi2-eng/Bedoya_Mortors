from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True # Si ya está logueado, lo manda al Dashboard

class UserManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'accounts/manage.html'

    def test_func(self):
        # SOLO el Administrador puede ver esta pantalla
        return self.request.user.role == 'ADMIN'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Traer todos los usuarios del sistema
        context['users_list'] = User.objects.all().order_by('-date_joined')
        return context

class UserCreateAPI(APIView):
    def post(self, request, *args, **kwargs):
        # Doble validación de seguridad: Solo admins pueden crear usuarios
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado. Solo administradores."}, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        try:
            # Validar si el usuario ya existe
            if User.objects.filter(username=data.get('username')).exists():
                return Response({"error": "El nombre de usuario ya está en uso."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear el usuario encriptando la contraseña automáticamente
            user = User.objects.create_user(
                username=data.get('username'),
                password=data.get('password'),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                email=data.get('email', ''),
                role=data.get('role', 'SELLER')
            )
            return Response({"message": "Empleado registrado exitosamente."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)