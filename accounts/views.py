from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin
)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

User = get_user_model()


# =========================
# LOGIN
# =========================
class CustomLoginView(LoginView):

    template_name = 'accounts/login.html'

    redirect_authenticated_user = True

    def get_success_url(self):
        return '/'


# =========================
# LOGOUT
# =========================
class LogoutView(View):

    def get(self, request):

        logout(request)

        return redirect('/accounts/login/')


# =========================
# GESTION DE PERSONAL
# =========================
class UserManagementView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    TemplateView
):

    template_name = 'accounts/manage.html'

    def test_func(self):

        # SOLO ADMIN
        return self.request.user.role == 'ADMIN'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['users_list'] = (
            User.objects.all()
            .order_by('-date_joined')
        )

        return context


# =========================
# API CREAR USUARIOS
# =========================
class UserCreateAPI(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        # SOLO ADMIN
        if request.user.role != 'ADMIN':

            return Response(
                {
                    "error": "Acceso denegado. Solo administradores."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data

        try:

            username = data.get('username')
            password = data.get('password')

            # VALIDACIONES
            if not username or not password:

                return Response(
                    {
                        "error": "Usuario y contraseña son obligatorios."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # VALIDAR USUARIO EXISTENTE
            if User.objects.filter(username=username).exists():

                return Response(
                    {
                        "error": "El nombre de usuario ya está en uso."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # CREAR USUARIO
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                email=data.get('email', ''),
                role=data.get('role', 'SELLER')
            )

            return Response(
                {
                    "message": "Empleado registrado exitosamente.",
                    "user": user.username
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:

            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
# =========================
# API ESTADO / ELIMINAR USUARIOS
# =========================
class UserToggleActiveAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        target_user = get_object_or_404(User, id=user_id)
        
        # Evitar que el admin se desactive a sí mismo
        if target_user == request.user:
            return Response({"error": "No puede desactivar su propia cuenta."}, status=status.HTTP_400_BAD_REQUEST)
            
        target_user.is_active = not target_user.is_active
        target_user.save()
        
        estado = "activado" if target_user.is_active else "desactivado"
        return Response({"message": f"Usuario {estado} exitosamente."})

class UserDeleteAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
            
        target_user = get_object_or_404(User, id=user_id)
        
        if target_user == request.user:
            return Response({"error": "No puede eliminar su propia cuenta."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            target_user.delete()
            return Response({"message": "Usuario eliminado permanentemente."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "El usuario tiene registros asociados y no puede ser eliminado. Sugerencia: Desactívelo."}, status=status.HTTP_400_BAD_REQUEST)