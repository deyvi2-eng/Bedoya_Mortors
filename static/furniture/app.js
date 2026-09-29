/* =========================================================
   Muebles M&L — componentes de interfaz (sin dependencias)
   ========================================================= */
(function () {
    'use strict';

    const FM = (window.FM = {});
    FM.csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';

    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    FM.esc = esc;

    FM.money = (n) => '$' + (Number(n) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    FM.num = (v) => {
        const n = parseFloat(String(v ?? '').replace(',', '.'));
        return Number.isFinite(n) ? n : 0;
    };

    /* ---------------- Avisos ---------------- */
    FM.toast = function (message, type = 'success') {
        const box = document.getElementById('toasts');
        if (!box) return alert(message);
        const styles = {
            success: ['bg-stone-900 text-white', 'ph-check-circle text-green-400'],
            error: ['bg-red-600 text-white', 'ph-warning-circle text-white'],
            info: ['bg-white text-stone-800 border border-stone-200', 'ph-info text-wood-500'],
        };
        const [cls, icon] = styles[type] || styles[type === 'warning' ? 'error' : 'info'] || styles.info;
        const el = document.createElement('div');
        el.className = `pointer-events-auto pop flex items-start gap-3 px-4 py-3.5 rounded-2xl shadow-lift font-semibold text-[15px] ${cls}`;
        el.innerHTML = `<i class="ph-fill ${icon} text-xl shrink-0"></i><span class="flex-1">${esc(message)}</span>`;
        box.appendChild(el);
        setTimeout(() => { el.style.transition = 'opacity .3s'; el.style.opacity = '0'; }, type === 'error' ? 5000 : 3000);
        setTimeout(() => el.remove(), type === 'error' ? 5400 : 3400);
    };

    /* ---------------- Hojas / modales ---------------- */
    FM.openSheet = function (id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        const first = el.querySelector('[autofocus]');
        if (first) setTimeout(() => first.focus(), 60);
    };
    FM.closeSheet = function (id) {
        const el = typeof id === 'string' ? document.getElementById(id) : id;
        if (!el) return;
        el.classList.add('hidden');
        if (!document.querySelector('[role="dialog"]:not(.hidden)')) document.body.style.overflow = '';
    };
    document.addEventListener('click', (e) => {
        const closer = e.target.closest('[data-close]');
        if (closer) FM.closeSheet(closer.closest('[role="dialog"]'));
    });
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        const open = [...document.querySelectorAll('[role="dialog"]:not(.hidden)')].pop();
        if (open) FM.closeSheet(open);
    });

    /* ---------------- Peticiones ---------------- */
    FM.postJSON = async function (url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': FM.csrf },
            body: JSON.stringify(data),
        });
        let body = {};
        try { body = await res.json(); } catch (e) { /* respuesta vacía */ }
        return { ok: res.ok, status: res.status, body };
    };

    /** Envía un FormData y sigue la redirección que indique el servidor. */
    FM.submit = async function (url, formData, button, onSuccess) {
        const original = button ? button.innerHTML : '';
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="ph-bold ph-spinner-gap animate-spin text-xl"></i> Guardando…';
        }
        try {
            const res = await fetch(url, { method: 'POST', headers: { 'X-CSRFToken': FM.csrf }, body: formData });
            let body = {};
            try { body = await res.json(); } catch (e) { /* no JSON */ }
            if (!res.ok) throw new Error(body.error || 'No se pudo guardar. Revise su conexión e intente de nuevo.');
            if (onSuccess) onSuccess(body);
            if (body.redirect) window.location.href = body.redirect;
            return body;
        } catch (err) {
            FM.toast(err.message === 'Failed to fetch' ? 'Sin conexión a internet. Sus datos siguen aquí, intente de nuevo.' : err.message, 'error');
            if (button) { button.disabled = false; button.innerHTML = original; }
            throw err;
        }
    };

    /* ---------------- Borrador automático ---------------- */
    FM.Draft = function (key) {
        const k = 'fm-draft:' + key;
        return {
            load() { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } },
            save(data) { try { localStorage.setItem(k, JSON.stringify({ ...data, _at: Date.now() })); } catch (e) { /* sin espacio */ } },
            clear() { try { localStorage.removeItem(k); } catch (e) { /* ignorar */ } },
        };
    };

    /* ---------------- Compresión de fotos ---------------- */
    FM.compressImage = function (file, maxSide = 1600, quality = 0.8) {
        return new Promise((resolve) => {
            if (!file.type.startsWith('image/') || file.type === 'image/gif') return resolve(file);
            const url = URL.createObjectURL(file);
            const img = new Image();
            img.onload = () => {
                const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
                const canvas = document.createElement('canvas');
                canvas.width = Math.round(img.width * scale);
                canvas.height = Math.round(img.height * scale);
                canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
                canvas.toBlob((blob) => {
                    URL.revokeObjectURL(url);
                    if (!blob || blob.size >= file.size) return resolve(file);
                    const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
                    resolve(new File([blob], name, { type: 'image/jpeg' }));
                }, 'image/jpeg', quality);
            };
            img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
            img.src = url;
        });
    };

    /* ---------------- Fotos ---------------- */
    FM.PhotoPicker = function (root, opts = {}) {
        const max = opts.max || 15;
        const photos = []; // { file, url, caption }
        const grid = root.querySelector('[data-photo-grid]');
        const counter = root.querySelector('[data-photo-count]');

        root.querySelectorAll('input[type=file]').forEach((input) => {
            input.addEventListener('change', async () => {
                const files = [...input.files];
                input.value = '';
                if (photos.length + files.length > max) FM.toast(`Máximo ${max} fotos.`, 'error');
                for (const f of files.slice(0, max - photos.length)) {
                    const file = await FM.compressImage(f);
                    photos.push({ file, url: URL.createObjectURL(file), caption: '' });
                }
                render();
            });
        });

        function render() {
            if (counter) counter.textContent = photos.length ? `${photos.length} foto${photos.length > 1 ? 's' : ''}` : '';
            grid.innerHTML = photos.map((p, i) => `
                <div class="relative rounded-2xl overflow-hidden bg-stone-100 border border-stone-200 pop">
                    <img src="${p.url}" class="w-full aspect-square object-cover" alt="">
                    <button type="button" data-remove="${i}" class="absolute top-2 right-2 w-9 h-9 rounded-full bg-black/60 text-white flex items-center justify-center backdrop-blur" aria-label="Quitar foto"><i class="ph-bold ph-x"></i></button>
                    <input type="text" data-caption="${i}" value="${esc(p.caption)}" placeholder="Nota (opcional)" class="w-full px-3 py-2 text-sm bg-white border-t border-stone-200 outline-none">
                </div>`).join('');
            grid.classList.toggle('hidden', !photos.length);
            if (opts.onChange) opts.onChange(photos.length);
        }

        grid.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-remove]');
            if (!btn) return;
            const [removed] = photos.splice(+btn.dataset.remove, 1);
            URL.revokeObjectURL(removed.url);
            render();
        });
        grid.addEventListener('input', (e) => {
            if (e.target.dataset.caption !== undefined) photos[+e.target.dataset.caption].caption = e.target.value;
        });

        render();
        return {
            count: () => photos.length,
            appendTo(fd) {
                photos.forEach((p) => { fd.append('photos', p.file); fd.append('photo_captions', p.caption); });
            },
        };
    };

    /* ---------------- Ítems (cantidad × valor) ---------------- */
    FM.ItemsEditor = function (root, opts = {}) {
        let items = (opts.items && opts.items.length ? opts.items : [{}]).map((i) => ({
            quantity: i.quantity ?? '1', description: i.description ?? '', unit_price: i.unit_price ?? '',
        }));
        const list = root.querySelector('[data-items]');
        const totalEl = document.querySelectorAll(opts.totalSelector || '[data-items-total]');

        const lineTotal = (i) => FM.num(i.quantity) * FM.num(i.unit_price);
        const total = () => items.reduce((s, i) => s + (i.description.trim() ? lineTotal(i) : 0), 0);

        function row(i, idx) {
            return `
            <div class="rounded-2xl border border-stone-200 bg-white p-3 sm:p-2 sm:pl-3 grid grid-cols-12 gap-2 items-center" data-row="${idx}">
                <input data-f="description" value="${esc(i.description)}" placeholder="Ej: Retapizado sofá 3 puestos" class="field col-span-10 sm:col-span-6 !py-2.5" autocomplete="off">
                <button type="button" data-del class="col-span-2 sm:col-span-1 sm:order-last w-10 h-10 rounded-xl text-stone-400 hover:bg-red-50 hover:text-red-600 flex items-center justify-center justify-self-end" aria-label="Quitar"><i class="ph-bold ph-trash text-lg"></i></button>
                <div class="col-span-3 sm:col-span-1">
                    <label class="sm:hidden text-[11px] font-bold text-stone-400">Cant.</label>
                    <input data-f="quantity" value="${esc(i.quantity)}" inputmode="decimal" class="field !px-2 !py-2.5 text-center">
                </div>
                <div class="col-span-4 sm:col-span-2">
                    <label class="sm:hidden text-[11px] font-bold text-stone-400">V. unitario</label>
                    <div class="relative"><span class="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400 font-bold">$</span>
                    <input data-f="unit_price" value="${esc(i.unit_price)}" inputmode="decimal" placeholder="0.00" class="field !pl-7 !py-2.5"></div>
                </div>
                <div class="col-span-5 sm:col-span-2 text-right">
                    <label class="sm:hidden text-[11px] font-bold text-stone-400">V. total</label>
                    <p class="font-extrabold text-[17px] py-2.5" data-line-total>${FM.money(lineTotal(i))}</p>
                </div>
            </div>`;
        }

        function render() {
            list.innerHTML = items.map(row).join('');
            refreshTotals();
        }
        function refreshTotals() {
            const t = total();
            totalEl.forEach((el) => (el.textContent = FM.money(t)));
            if (opts.onChange) opts.onChange(t);
        }

        list.addEventListener('input', (e) => {
            const r = e.target.closest('[data-row]');
            if (!r) return;
            const i = items[+r.dataset.row];
            i[e.target.dataset.f] = e.target.value;
            r.querySelector('[data-line-total]').textContent = FM.money(lineTotal(i));
            refreshTotals();
        });
        list.addEventListener('click', (e) => {
            if (!e.target.closest('[data-del]')) return;
            items.splice(+e.target.closest('[data-row]').dataset.row, 1);
            if (!items.length) items.push({ quantity: '1', description: '', unit_price: '' });
            render();
        });
        root.querySelector('[data-add-item]').addEventListener('click', () => {
            items.push({ quantity: '1', description: '', unit_price: '' });
            render();
            list.querySelector('[data-row]:last-child [data-f=description]').focus();
        });

        render();
        return {
            total,
            get: () => items.filter((i) => i.description.trim()),
            all: () => items,
            set(list) {
                items = list.map((i) => ({ quantity: i.quantity ?? '1', description: i.description ?? '', unit_price: i.unit_price ?? '' }));
                if (!items.length) items.push({ quantity: '1', description: '', unit_price: '' });
                render();
            },
        };
    };

    /* ---------------- Modal de cliente (crear / editar) ---------------- */
    let clientModal;
    function buildClientModal() {
        const wrap = document.createElement('div');
        wrap.id = 'client-modal';
        wrap.className = 'fixed inset-0 z-[70] hidden';
        wrap.setAttribute('role', 'dialog');
        wrap.setAttribute('aria-modal', 'true');
        wrap.innerHTML = `
        <div class="absolute inset-0 bg-stone-900/50 backdrop-blur-sm" data-close></div>
        <div class="absolute inset-x-0 bottom-0 sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-[520px] bg-white rounded-t-[2rem] sm:rounded-[2rem] max-h-[92dvh] flex flex-col pop">
            <div class="flex items-center justify-between px-5 pt-5 pb-3">
                <h3 class="text-xl font-extrabold" data-title>Nuevo cliente</h3>
                <button type="button" data-close class="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center"><i class="ph-bold ph-x text-lg"></i></button>
            </div>
            <form class="px-5 pb-2 space-y-3 overflow-y-auto" autocomplete="off" novalidate>
                <div><label class="label">Nombre completo *</label><input name="name" class="field" required autofocus placeholder="Ej: María López"></div>
                <div><label class="label">Celular / WhatsApp *</label><input name="phone" class="field" inputmode="tel" required placeholder="0991234567"></div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="label">Cédula / RUC</label><input name="id_number" class="field" inputmode="numeric" maxlength="13"></div>
                    <div><label class="label">Correo</label><input name="email" type="email" class="field" inputmode="email"></div>
                </div>
                <div><label class="label">Dirección</label><input name="address" class="field" placeholder="Barrio, calle, referencia"></div>
                <p class="text-sm font-bold text-red-600 hidden" data-error></p>
            </form>
            <div class="flex gap-3 p-5 border-t border-stone-100 safe-bottom">
                <button type="button" data-close class="btn btn-soft flex-1 sm:flex-none">Cancelar</button>
                <button type="button" data-save class="btn btn-primary flex-1"><i class="ph-bold ph-check text-lg"></i> Guardar cliente</button>
            </div>
        </div>`;
        document.body.appendChild(wrap);
        return wrap;
    }

    FM.openClientModal = function ({ client = null, prefill = {}, onSaved } = {}) {
        clientModal = clientModal || buildClientModal();
        const form = clientModal.querySelector('form');
        const err = clientModal.querySelector('[data-error]');
        const save = clientModal.querySelector('[data-save]');
        form.reset();
        err.classList.add('hidden');
        const data = client || prefill;
        ['name', 'phone', 'id_number', 'email', 'address'].forEach((f) => (form.elements[f].value = data[f] || ''));
        clientModal.querySelector('[data-title]').textContent = client ? 'Editar cliente' : 'Nuevo cliente';

        const fresh = save.cloneNode(true); // quita listeners anteriores
        save.replaceWith(fresh);
        const submit = async () => {
            const payload = Object.fromEntries(new FormData(form).entries());
            fresh.disabled = true;
            const url = client ? `/muebles/api/clientes/${client.id}/guardar/` : '/muebles/api/clientes/guardar/';
            let res;
            try { res = await FM.postJSON(url, payload); }
            catch (e) { res = { ok: false, body: { error: 'Sin conexión. Intente de nuevo.' } }; }
            fresh.disabled = false;
            if (!res.ok) {
                err.textContent = res.body.error || 'No se pudo guardar.';
                err.classList.remove('hidden');
                return;
            }
            FM.closeSheet(clientModal);
            FM.toast(client ? 'Cliente actualizado' : 'Cliente creado');
            if (onSaved) onSaved(res.body.client);
        };
        fresh.addEventListener('click', submit);
        form.onsubmit = (e) => { e.preventDefault(); submit(); };
        form.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); submit(); } };
        FM.openSheet('client-modal');
    };

    /* ---------------- Selector de cliente ---------------- */
    FM.ClientPicker = function (root, opts = {}) {
        const hidden = root.querySelector('input[name=client_id]');
        const search = root.querySelector('[data-client-search]');
        const results = root.querySelector('[data-client-results]');
        const selectedBox = root.querySelector('[data-client-selected]');
        const searchBox = root.querySelector('[data-client-searchbox]');
        let current = null;
        let timer;

        function select(client) {
            current = client;
            hidden.value = client ? client.id : '';
            searchBox.classList.toggle('hidden', !!client);
            selectedBox.classList.toggle('hidden', !client);
            results.classList.add('hidden');
            if (client) {
                selectedBox.querySelector('[data-name]').textContent = client.name;
                selectedBox.querySelector('[data-meta]').textContent = [client.phone, client.id_number].filter(Boolean).join(' · ');
            } else {
                search.value = '';
                setTimeout(() => search.focus(), 50);
            }
            if (opts.onChange) opts.onChange(client);
        }

        function createOption(q) {
            const isPhone = /^[\d\s+]+$/.test(q);
            const prefill = q ? (isPhone ? { phone: q } : { name: q }) : {};
            return { prefill, html: `
                <button type="button" data-create class="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-wood-50 text-wood-700 font-extrabold">
                    <span class="w-10 h-10 rounded-xl bg-wood-500 text-white flex items-center justify-center"><i class="ph-bold ph-user-plus text-lg"></i></span>
                    ${q ? `Crear cliente “${esc(q)}”` : 'Crear cliente nuevo'}
                </button>` };
        }

        async function lookup() {
            const q = search.value.trim();
            let list = [];
            try {
                const res = await fetch('/muebles/api/clientes/?q=' + encodeURIComponent(q));
                list = (await res.json()).results || [];
            } catch (e) { /* sin conexión: solo mostramos "crear" */ }
            const create = createOption(q);
            results.innerHTML = create.html + list.map((c, i) => `
                <button type="button" data-pick="${i}" class="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-stone-50">
                    <span class="w-10 h-10 rounded-xl bg-stone-100 text-stone-600 flex items-center justify-center font-extrabold">${esc(c.name[0] || '?').toUpperCase()}</span>
                    <span class="min-w-0"><span class="block font-bold truncate">${esc(c.name)}</span><span class="block text-sm text-stone-400">${esc(c.phone)}${c.id_number ? ' · ' + esc(c.id_number) : ''}</span></span>
                </button>`).join('');
            const wasHidden = results.classList.contains('hidden');
            results.classList.remove('hidden');
            // En celular el teclado y la barra inferior tapan la lista: subimos el buscador
            if (wasHidden && window.innerWidth < 1024) search.scrollIntoView({ block: 'start', behavior: 'smooth' });
            results.querySelectorAll('[data-pick]').forEach((b) => b.addEventListener('click', () => select(list[+b.dataset.pick])));
            results.querySelector('[data-create]').addEventListener('click', () =>
                FM.openClientModal({ prefill: create.prefill, onSaved: select }));
        }

        search.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(lookup, 220); });
        search.addEventListener('focus', lookup);
        document.addEventListener('click', (e) => { if (!root.contains(e.target)) results.classList.add('hidden'); });
        root.querySelector('[data-client-change]').addEventListener('click', () => select(null));
        root.querySelector('[data-client-edit]')?.addEventListener('click', () =>
            FM.openClientModal({ client: current, onSaved: select }));
        root.querySelector('[data-client-new]')?.addEventListener('click', () =>
            FM.openClientModal({ prefill: {}, onSaved: select }));

        if (opts.initial) select(opts.initial);
        return { get: () => current, set: select };
    };

    /* ---------------- Firma digital (pantalla completa) ---------------- */
    let sigOverlay;
    function buildSignatureOverlay() {
        const el = document.createElement('div');
        el.className = 'fixed inset-0 z-[80] hidden bg-stone-100 flex flex-col';
        el.setAttribute('role', 'dialog');
        el.innerHTML = `
            <div class="flex items-center justify-between px-4 h-16 bg-white border-b border-stone-200 shrink-0">
                <div><p class="font-extrabold text-lg leading-tight" data-sig-title>Firma</p><p class="text-xs text-stone-400">Firme con el dedo dentro del recuadro</p></div>
                <button type="button" data-sig-cancel class="w-11 h-11 rounded-xl bg-stone-100 flex items-center justify-center"><i class="ph-bold ph-x text-xl"></i></button>
            </div>
            <div class="flex-1 p-3 sm:p-6 min-h-0">
                <div class="relative w-full h-full bg-white rounded-3xl border-2 border-dashed border-stone-300 overflow-hidden">
                    <canvas class="absolute inset-0 w-full h-full touch-none cursor-crosshair"></canvas>
                    <div class="absolute left-6 right-6 bottom-[22%] border-b-2 border-stone-200 pointer-events-none"></div>
                    <p class="absolute left-6 bottom-[calc(22%-1.75rem)] text-xs font-bold text-stone-300 pointer-events-none">✕ Firme sobre la línea</p>
                </div>
            </div>
            <div class="flex gap-3 p-3 sm:px-6 sm:pb-6 bg-stone-100 safe-bottom shrink-0">
                <button type="button" data-sig-clear class="btn btn-soft bg-white flex-1 sm:flex-none"><i class="ph-bold ph-eraser text-lg"></i> Borrar</button>
                <button type="button" data-sig-ok class="btn btn-primary flex-1 text-[17px]"><i class="ph-bold ph-check text-lg"></i> Listo</button>
            </div>`;
        document.body.appendChild(el);
        return el;
    }

    function openSignature(title, onDone) {
        sigOverlay = sigOverlay || buildSignatureOverlay();
        const canvas = sigOverlay.querySelector('canvas');
        sigOverlay.querySelector('[data-sig-title]').textContent = title;
        sigOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const ctx = canvas.getContext('2d');
        let sized = '';
        // El lienzo se mide cuando ya tiene su tamaño real en pantalla
        // (la primera vez los estilos del overlay se aplican un instante después).
        function fit() {
            const rect = canvas.getBoundingClientRect();
            const key = Math.round(rect.width) + 'x' + Math.round(rect.height);
            if (key === sized || rect.width < 10) return;
            sized = key;
            canvas.width = rect.width * ratio;
            canvas.height = rect.height * ratio;
            ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.strokeStyle = '#0f172a';
            ctx.lineWidth = 2.6;
        }
        requestAnimationFrame(() => requestAnimationFrame(fit));

        let drawing = false, last = null, empty = true;
        let box = { x1: Infinity, y1: Infinity, x2: -Infinity, y2: -Infinity };
        const pos = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
        const grow = (p) => { box.x1 = Math.min(box.x1, p.x); box.y1 = Math.min(box.y1, p.y); box.x2 = Math.max(box.x2, p.x); box.y2 = Math.max(box.y2, p.y); };

        canvas.onpointerdown = (e) => { if (empty) fit(); drawing = true; last = pos(e); grow(last); canvas.setPointerCapture(e.pointerId); ctx.beginPath(); ctx.arc(last.x, last.y, 1.2, 0, Math.PI * 2); ctx.fillStyle = '#0f172a'; ctx.fill(); empty = false; };
        canvas.onpointermove = (e) => {
            if (!drawing) return;
            const p = pos(e);
            const mid = { x: (last.x + p.x) / 2, y: (last.y + p.y) / 2 };
            ctx.beginPath();
            ctx.moveTo(last.x, last.y);
            ctx.quadraticCurveTo(last.x, last.y, mid.x, mid.y);
            ctx.lineTo(p.x, p.y);
            ctx.stroke();
            last = p; grow(p); empty = false;
        };
        canvas.onpointerup = canvas.onpointercancel = () => { drawing = false; };

        const close = () => { sigOverlay.classList.add('hidden'); document.body.style.overflow = ''; };
        sigOverlay.querySelector('[data-sig-clear]').onclick = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            empty = true; box = { x1: Infinity, y1: Infinity, x2: -Infinity, y2: -Infinity };
        };
        sigOverlay.querySelector('[data-sig-cancel]').onclick = close;
        sigOverlay.querySelector('[data-sig-ok]').onclick = () => {
            if (empty) return FM.toast('Firme antes de continuar', 'error');
            // Recorta la firma para que el PDF no tenga espacios en blanco enormes
            const pad = 16;
            const sx = Math.max(0, (box.x1 - pad) * ratio), sy = Math.max(0, (box.y1 - pad) * ratio);
            const sw = Math.min(canvas.width - sx, (box.x2 - box.x1 + pad * 2) * ratio);
            const sh = Math.min(canvas.height - sy, (box.y2 - box.y1 + pad * 2) * ratio);
            const out = document.createElement('canvas');
            const scale = Math.min(1, 900 / sw);
            out.width = Math.max(1, sw * scale); out.height = Math.max(1, sh * scale);
            const o = out.getContext('2d');
            o.fillStyle = '#fff'; o.fillRect(0, 0, out.width, out.height);
            o.drawImage(canvas, sx, sy, sw, sh, 0, 0, out.width, out.height);
            close();
            onDone(out.toDataURL('image/png'));
        };
    }

    FM.SignatureField = function (root, opts = {}) {
        let value = '';
        const preview = root.querySelector('[data-sig-preview]');
        const empty = root.querySelector('[data-sig-empty]');
        root.querySelector('[data-sig-open]').addEventListener('click', () =>
            openSignature(opts.title || 'Firma', (dataUrl) => {
                value = dataUrl;
                preview.src = dataUrl;
                preview.classList.remove('hidden');
                empty.classList.add('hidden');
                root.classList.add('border-green-400', 'bg-green-50/40');
                if (opts.onChange) opts.onChange(value);
            }));
        return { value: () => value };
    };

    /* ---------------- Dictado por voz (gratis, del navegador) ---------------- */
    FM.initDictation = function (scope = document) {
        const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
        scope.querySelectorAll('[data-dictate]').forEach((btn) => {
            if (!Rec) { btn.remove(); return; }
            const target = document.getElementById(btn.dataset.dictate);
            let rec = null;
            btn.addEventListener('click', () => {
                if (rec) { rec.stop(); return; }
                rec = new Rec();
                rec.lang = 'es-EC';
                rec.continuous = true;
                rec.interimResults = false;
                const base = target.value;
                let spoken = '';
                btn.classList.add('!bg-red-600', '!text-white', 'animate-pulse');
                btn.querySelector('span') && (btn.querySelector('span').textContent = 'Escuchando… toca para parar');
                rec.onresult = (e) => {
                    for (let i = e.resultIndex; i < e.results.length; i++) {
                        if (e.results[i].isFinal) spoken += (spoken ? ' ' : '') + e.results[i][0].transcript.trim();
                    }
                    const text = spoken.charAt(0).toUpperCase() + spoken.slice(1);
                    target.value = (base ? base.trimEnd() + (/[.!?]$/.test(base.trim()) ? ' ' : '. ') : '') + text;
                    target.dispatchEvent(new Event('input', { bubbles: true }));
                };
                rec.onerror = (e) => { if (e.error === 'not-allowed') FM.toast('Permita el uso del micrófono para dictar.', 'error'); };
                rec.onend = () => {
                    rec = null;
                    btn.classList.remove('!bg-red-600', '!text-white', 'animate-pulse');
                    btn.querySelector('span') && (btn.querySelector('span').textContent = 'Dictar');
                };
                rec.start();
            });
        });
    };

    /* ---------------- Compartir PDF (celular) ---------------- */
    FM.sharePdf = async function (url, filename, text) {
        try {
            const blob = await (await fetch(url)).blob();
            const file = new File([blob], filename, { type: 'application/pdf' });
            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                await navigator.share({ files: [file], text });
                return;
            }
        } catch (e) {
            if (e.name === 'AbortError') return;
        }
        window.open(url, '_blank');
    };

    FM.copy = async function (text) {
        try { await navigator.clipboard.writeText(text); FM.toast('Enlace copiado'); }
        catch (e) { prompt('Copie el enlace:', text); }
    };

    document.addEventListener('DOMContentLoaded', () => FM.initDictation());
})();
