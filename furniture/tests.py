import base64
import io
import json
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from companies.models import Company

from .models import Client, Order, OrderPhoto, Quote

User = get_user_model()
MEDIA = tempfile.mkdtemp()
LOCAL_STORAGE = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def png_data_url():
    buf = io.BytesIO()
    img = Image.new('RGBA', (120, 40), (0, 0, 0, 0))
    img.putpixel((10, 10), (0, 0, 0, 255))
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def jpeg_upload(name='foto.jpg'):
    buf = io.BytesIO()
    Image.new('RGB', (300, 200), (180, 120, 60)).save(buf, format='JPEG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


@override_settings(STORAGES=LOCAL_STORAGE, MEDIA_ROOT=MEDIA)
class FurnitureTestBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.muebles = User.objects.create_user('taller', password='clave123', role='MUEBLES', first_name='Luis')
        self.seller = User.objects.create_user('vendedor', password='clave123', role='SELLER')
        self.admin = User.objects.create_user('jefe', password='clave123', role='ADMIN')
        self.client_obj = Client.objects.create(name='María López', phone='0991234567')


class AccessTests(FurnitureTestBase):
    def test_login_redirects_muebles_user_to_furniture(self):
        res = self.client.post(reverse('accounts:login'), {'username': 'taller', 'password': 'clave123'})
        self.assertRedirects(res, '/muebles/', fetch_redirect_response=False)

    def test_muebles_user_cannot_open_bedoya_pages(self):
        self.client.force_login(self.muebles)
        res = self.client.get('/sales/pos/')
        self.assertRedirects(res, '/muebles/', fetch_redirect_response=False)

    def test_seller_cannot_open_furniture(self):
        self.client.force_login(self.seller)
        res = self.client.get('/muebles/')
        self.assertEqual(res.status_code, 302)
        self.assertNotEqual(res['Location'], '/muebles/')

    def test_admin_can_open_both(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/muebles/').status_code, 200)
        self.assertEqual(self.client.get(reverse('companies:list')).status_code, 200)

    def test_all_furniture_pages_render(self):
        self.client.force_login(self.muebles)
        quote = Quote.objects.create(client=self.client_obj, kind='RETAPIZADO')
        order = Order.objects.create(client=self.client_obj, kind='FABRICACION')
        urls = [
            reverse('furniture:home'), reverse('furniture:clients'),
            reverse('furniture:client_detail', args=[self.client_obj.pk]),
            reverse('furniture:orders'), reverse('furniture:orders') + '?estado=todas&q=maria',
            reverse('furniture:order_create') + '?tipo=RETAPIZADO',
            reverse('furniture:order_create') + f'?proforma={quote.pk}',
            reverse('furniture:order_detail', args=[order.pk]) + '?nueva=1',
            reverse('furniture:quotes'), reverse('furniture:quote_create'),
            reverse('furniture:quote_detail', args=[quote.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_public_pdf_needs_no_login(self):
        order = Order.objects.create(client=self.client_obj, kind='RETAPIZADO')
        res = self.client.get(reverse('furniture:public_order_pdf', args=[order.public_token]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')


class ClientApiTests(FurnitureTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.muebles)

    def test_create_client_returns_json(self):
        res = self.client.post(reverse('furniture:client_create_api'),
                               data=json.dumps({'name': 'Pedro Ruiz', 'phone': '0987654321'}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['client']['name'], 'Pedro Ruiz')

    def test_invalid_phone_is_rejected(self):
        res = self.client.post(reverse('furniture:client_create_api'),
                               data=json.dumps({'name': 'Pedro', 'phone': '12'}), content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_search(self):
        res = self.client.get(reverse('furniture:client_search_api') + '?q=0991')
        self.assertEqual(res.json()['results'][0]['name'], 'María López')

    def test_whatsapp_number_format(self):
        self.assertEqual(self.client_obj.whatsapp_number, '593991234567')


class OrderFlowTests(FurnitureTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.muebles)
        company = Company.furniture()
        company.ruc = '1790012345001'
        company.save()

    def post_order(self, **extra):
        data = {
            'kind': 'RETAPIZADO',
            'client_id': self.client_obj.pk,
            'observations': 'Tela rota en brazo',
            'requirements': 'Cuero café',
            'items': json.dumps([
                {'quantity': '2', 'description': 'Cojín', 'unit_price': '15.50'},
                {'quantity': '1', 'description': '', 'unit_price': '99'},  # fila vacía: se ignora
            ]),
            'deposit': '10',
            'delivery_date': '2026-10-15',
            'owner_signer_name': 'Luis',
            'owner_signature': png_data_url(),
            'client_signature': png_data_url(),
            'photos': [jpeg_upload('a.jpg'), jpeg_upload('b.jpg')],
            'photo_captions': ['frente', 'lado'],
        }
        data.update(extra)
        return self.client.post(reverse('furniture:order_create'), data)

    def test_create_order_full_flow(self):
        res = self.post_order()
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.get()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total, Decimal('31.00'))
        self.assertEqual(order.balance, Decimal('21.00'))
        self.assertEqual(order.photos.filter(stage=OrderPhoto.Stage.CURRENT).count(), 2)
        self.assertTrue(order.client_signature and order.owner_signature)
        self.assertEqual(order.company_snapshot['ruc'], '1790012345001')
        self.assertEqual(order.status_logs.count(), 1)

        pdf = self.client.get(reverse('furniture:order_pdf', args=[order.pk]))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))

        detail = self.client.get(reverse('furniture:order_detail', args=[order.pk]))
        self.assertContains(detail, 'https://wa.me/593991234567?text=')

    def test_signatures_are_required(self):
        res = self.post_order(client_signature='')
        self.assertEqual(res.status_code, 400)
        self.assertIn('firma del cliente', res.json()['error'])
        self.assertFalse(Order.objects.exists())

    def test_bad_price_is_rejected(self):
        res = self.post_order(items=json.dumps([{'quantity': '1', 'description': 'x', 'unit_price': 'abc'}]))
        self.assertEqual(res.status_code, 400)

    def test_status_payment_and_photos(self):
        self.post_order()
        order = Order.objects.get()
        self.client.post(reverse('furniture:order_status', args=[order.pk]), {'status': 'LISTO'})
        self.client.post(reverse('furniture:order_payment', args=[order.pk]), {'amount': '5.5'})
        res = self.client.post(reverse('furniture:order_add_photos', args=[order.pk]),
                               {'stage': 'TERMINADO', 'photos': [jpeg_upload()]})
        self.assertEqual(res.status_code, 201)
        order.refresh_from_db()
        self.assertEqual(order.status, 'LISTO')
        self.assertEqual(order.deposit, Decimal('15.50'))
        self.assertEqual(order.photos.filter(stage='TERMINADO').count(), 1)

    def test_quote_to_order(self):
        res = self.client.post(reverse('furniture:quote_create'), {
            'kind': 'FABRICACION', 'client_id': self.client_obj.pk, 'notes': 'Sofá en L',
            'items': json.dumps([{'quantity': '1', 'description': 'Sofá en L', 'unit_price': '450'}]),
            'valid_days': '10', 'photos': [jpeg_upload('ref.jpg')],
        })
        self.assertEqual(res.status_code, 201, res.content)
        quote = Quote.objects.get()
        self.assertEqual(quote.total, Decimal('450.00'))
        self.assertTrue(self.client.get(reverse('furniture:quote_pdf', args=[quote.pk])).content.startswith(b'%PDF'))

        res = self.post_order(kind='FABRICACION', quote_id=quote.pk, photos=[])
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.get()
        quote.refresh_from_db()
        self.assertEqual(quote.status, 'ACEPTADA')
        self.assertEqual(order.quote, quote)
        self.assertEqual(order.photos.filter(stage='REFERENCIA').count(), 1)


class UserAdminTests(FurnitureTestBase):
    def test_admin_edits_role_and_password(self):
        self.client.force_login(self.admin)
        res = self.client.post(reverse('accounts:api-update', args=[self.seller.pk]),
                               data=json.dumps({'username': 'vendedor', 'first_name': 'Ana', 'role': 'MUEBLES', 'password': 'nueva123'}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 200, res.content)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, 'MUEBLES')
        self.assertTrue(self.seller.check_password('nueva123'))

    def test_non_admin_cannot_edit(self):
        self.client.force_login(self.muebles)
        res = self.client.post(reverse('accounts:api-update', args=[self.seller.pk]),
                               data=json.dumps({'username': 'x', 'role': 'ADMIN'}), content_type='application/json')
        self.assertNotEqual(res.status_code, 200)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.role, 'SELLER')

    def test_manage_page_renders(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse('accounts:manage'))
        self.assertContains(res, 'Muebles M&amp;L')

    def test_company_edit(self):
        self.client.force_login(self.admin)
        Company.furniture()
        res = self.client.post(reverse('companies:edit', args=['muebles-ml']), {
            'name': 'Muebles M&L', 'ruc': '1790012345001', 'email': 'info@mueblesml.com',
            'logo': jpeg_upload('logo.jpg'),
        })
        self.assertEqual(res.status_code, 302)
        company = Company.furniture()
        self.assertEqual(company.email, 'info@mueblesml.com')
        self.assertTrue(company.logo)
