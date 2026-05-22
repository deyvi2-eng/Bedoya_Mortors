from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from .models import Customer

class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'customers/manage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mostrar todos los clientes activos ordenados por fecha de creación
        context['customers'] = Customer.objects.filter(is_active=True).order_by('-created_at')
        return context

class CustomerCreateAPI(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Extraer datos del payload
            data = request.data
            
            # Instanciar el modelo para que pasen las validaciones matemáticas de la cédula
            customer = Customer(
                cedula=data.get('cedula'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                phone=data.get('phone'),
                whatsapp=data.get('whatsapp', ''),
                email=data.get('email', ''),
                address=data.get('address'),
                city=data.get('city'),
                observations=data.get('observations', '')
            )
            
            # clean_fields() ejecuta el validador de cédula ecuatoriana de validators.py
            customer.clean_fields()
            customer.save()

            return Response({
                "message": "Cliente registrado exitosamente.",
                "customer_id": customer.id
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Capturar el error exacto de la cédula (Módulo 10) y enviarlo al Frontend
            error_msg = list(e.message_dict.values())[0][0] if hasattr(e, 'message_dict') else str(e.messages[0])
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "La cédula o correo ya existen en el sistema."}, status=status.HTTP_400_BAD_REQUEST)