{% extends 'base.html' %}

{% block title %}Gestión de Clientes | Bedoya Motors{% endblock %}
{% block header_title %}Cartera de Clientes{% endblock %}

{% block extra_head %}
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto space-y-6">

    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 md:p-6 rounded-2xl border border-gray-100 shadow-sm">
        <div>
            <h2 class="text-base font-bold text-gray-900 leading-none">Directorio de Clientes</h2>
            <p class="text-xs text-gray-400 mt-1">Registre compradores para emitir comprobantes autorizados.</p>
        </div>
        <button onclick="toggleModal('modal-customer')" class="w-full sm:w-auto bg-brand-600 hover:bg-brand-500 text-white font-bold py-3 px-5 rounded-xl text-xs shadow-md transition-all active:scale-95 flex items-center justify-center gap-2">
            <i class="ph-bold ph-user-plus text-lg"></i> Registrar Cliente
        </button>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-100">
                <thead class="bg-gray-50 text-xs font-bold text-gray-400 uppercase tracking-wider">
                    <tr>
                        <th class="px-6 py-4 text-left">Identificación</th>
                        <th class="px-6 py-4 text-left">Cliente</th>
                        <th class="px-6 py-4 text-left">Contacto</th>
                        <th class="px-6 py-4 text-left">Ubicación</th>
                        <th class="px-6 py-4 text-center">Registro</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50 text-sm text-gray-700">
                    {% for c in customers %}
                    <tr class="hover:bg-gray-50/50 transition-colors">
                        <td class="px-6 py-4 font-bold text-gray-900">{{ c.cedula }}</td>
                        <td class="px-6 py-4">
                            <div class="font-bold text-gray-900">{{ c.first_name }} {{ c.last_name }}</div>
                            <div class="text-xs text-gray-400">{{ c.email|default:"Sin correo" }}</div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-1.5"><i class="ph-fill ph-phone text-gray-400"></i> {{ c.phone }}</div>
                            {% if c.whatsapp %}
                                <div class="flex items-center gap-1.5 text-green-600 text-xs mt-1"><i class="ph-fill ph-whatsapp-logo"></i> {{ c.whatsapp }}</div>
                            {% endif %}
                        </td>
                        <td class="px-6 py-4 text-xs">{{ c.city }}<br><span class="text-gray-400">{{ c.address }}</span></td>
                        <td class="px-6 py-4 text-center text-xs text-gray-400">{{ c.created_at|date:"d M Y" }}</td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="5" class="px-6 py-12 text-center text-gray-400 text-xs">
                            <i class="ph ph-users text-4xl text-gray-200 mb-2 block"></i> No hay clientes registrados.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<div id="modal-customer" class="fixed inset-0 z-50 hidden bg-gray-900/40 backdrop-blur-sm overflow-y-auto w-full h-full">
    <div class="flex items-center justify-center min-h-screen p-4">
        <div class="relative bg-white rounded-2xl text-left overflow-hidden shadow-2xl transform transition-all max-w-2xl w-full border border-gray-100">
            <div class="px-6 py-4 bg-gray-50 border-b border-gray-100 flex justify-between items-center">
                <h3 class="text-sm font-bold text-gray-900 uppercase tracking-wider">Alta de Cliente</h3>
                <button onclick="toggleModal('modal-customer')" class="text-gray-400 hover:text-gray-600"><i class="ph-bold ph-x text-lg"></i></button>
            </div>
            
            <div class="p-6">
                <form id="form-customer" class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Cédula de Identidad *</label>
                            <input type="text" id="c_cedula" maxlength="10" required class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ciudad *</label>
                            <input type="text" id="c_city" value="Sangolquí" required class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Nombres *</label>
                            <input type="text" id="c_first_name" required class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Apellidos *</label>
                            <input type="text" id="c_last_name" required class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Teléfono Fijo / Celular *</label>
                            <input type="text" id="c_phone" required class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">WhatsApp</label>
                            <input type="text" id="c_whatsapp" class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Correo Electrónico</label>
                        <input type="email" id="c_email" class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Dirección Exacta *</label>
                        <input type="text" id="c_address" required class="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl px-3 py-2.5 outline-none text-sm focus:ring-2 focus:ring-brand-500">
                    </div>
                </form>
            </div>
            
            <div class="bg-gray-50 px-6 py-3 flex justify-end gap-2 border-t border-gray-100">
                <button type="button" onclick="toggleModal('modal-customer')" class="px-4 py-2 text-xs font-medium text-gray-500 bg-white border border-gray-200 rounded-lg">Cancelar</button>
                <button type="button" id="btn-save-customer" class="px-4 py-2 text-xs font-bold text-white bg-brand-600 rounded-lg hover:bg-brand-500 shadow-md">Guardar Cliente</button>
            </div>
        </div>
    </div>
</div>

<script>
    const getCSRFToken = () => document.cookie.split('; ').find(r => r.startsWith('csrftoken=')).split('=')[1];
    const toggleModal = (id) => document.getElementById(id).classList.toggle('hidden');

    document.getElementById('btn-save-customer').addEventListener('click', function() {
        const form = document.getElementById('form-customer');
        if(!form.checkValidity()) return form.reportValidity();

        const payload = {
            cedula: document.getElementById('c_cedula').value,
            first_name: document.getElementById('c_first_name').value,
            last_name: document.getElementById('c_last_name').value,
            city: document.getElementById('c_city').value,
            address: document.getElementById('c_address').value,
            phone: document.getElementById('c_phone').value,
            whatsapp: document.getElementById('c_whatsapp').value,
            email: document.getElementById('c_email').value
        };

        this.disabled = true;
        this.innerText = 'Validando SRI...';

        fetch('/customers/api/create/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify(payload)
        })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(result => {
            if (result.status === 201) {
                Swal.fire({ title: 'Éxito', text: 'Cliente registrado correctamente.', icon: 'success', confirmButtonColor: '#0d9488' })
                .then(() => window.location.reload());
            } else {
                // Muestra si la cédula es falsa o inválida
                Swal.fire('Error de Validación', result.body.error, 'error');
                this.disabled = false;
                this.innerText = 'Guardar Cliente';
            }
        });
    });
</script>
{% endblock %}