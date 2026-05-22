from django.views import View
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from sales.models import Sale
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from django.utils.timezone import localtime

class ExportSalesExcelView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        # Crear libro de trabajo en memoria
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte de Ventas"

        # Estilos corporativos para cabeceras
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid") # Tailwind Brand-600
        alignment_center = Alignment(horizontal="center", vertical="center")

        # Definir cabeceras
        headers = ['Factura', 'Fecha', 'Cliente', 'Cédula', 'Vendedor', 'Método Pago', 'Estado', 'Total ($)']
        ws.append(headers)

        # Aplicar estilos a la primera fila
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = alignment_center

        # Obtener datos de la base de datos (Ejemplo: mes actual o histórico completo)
        ventas = Sale.objects.select_related('customer', 'seller').order_by('-created_at')

        # Poblar filas
        for venta in ventas:
            fecha_local = localtime(venta.created_at).strftime("%Y-%m-%d %H:%M")
            estado = "ANULADA" if venta.is_voided else "PROCESADA"
            
            row = [
                venta.invoice_number,
                fecha_local,
                f"{venta.customer.first_name} {venta.customer.last_name}",
                venta.customer.cedula,
                venta.seller.get_full_name(),
                venta.get_payment_method_display(),
                estado,
                float(venta.total)
            ]
            ws.append(row)

        # Ajustar ancho de columnas automáticamente
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[col_letter].width = max_length + 4

        # Preparar respuesta HTTP
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Reporte_Ventas_BedoyaMotors.xlsx"'
        wb.save(response)

        return response