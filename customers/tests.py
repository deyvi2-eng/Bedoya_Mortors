from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Customer
from .validators import normalize_identification


def cedula_ec(base9):
    """Completa una cédula ecuatoriana válida a partir de sus 9 primeros dígitos."""
    total = 0
    for i, coef in enumerate([2, 1, 2, 1, 2, 1, 2, 1, 2]):
        x = int(base9[i]) * coef
        total += x if x < 10 else x - 9
    return base9 + str((10 - total % 10) % 10)


CEDULA_OK = cedula_ec('171003406')


class IdentificationValidatorTests(TestCase):
    def assertInvalid(self, id_type, value):
        with self.assertRaises(ValidationError):
            normalize_identification(id_type, value)

    def test_empty_is_allowed(self):
        self.assertIsNone(normalize_identification('CEDULA_EC', '  '))

    def test_cedula_ecuador(self):
        self.assertEqual(normalize_identification('CEDULA_EC', CEDULA_OK), CEDULA_OK)
        bad_digit = CEDULA_OK[:9] + str((int(CEDULA_OK[9]) + 1) % 10)
        self.assertInvalid('CEDULA_EC', bad_digit)
        self.assertInvalid('CEDULA_EC', '123')
        self.assertInvalid('CEDULA_EC', cedula_ec('991234567'))  # provincia 99

    def test_ruc_ecuador(self):
        self.assertEqual(normalize_identification('RUC_EC', CEDULA_OK + '001'), CEDULA_OK + '001')
        self.assertEqual(normalize_identification('RUC_EC', '1790012345001'), '1790012345001')  # sociedad
        self.assertEqual(normalize_identification('RUC_EC', '1760001550001'), '1760001550001')  # pública
        self.assertInvalid('RUC_EC', CEDULA_OK + '000')
        self.assertInvalid('RUC_EC', CEDULA_OK)          # 10 dígitos no es RUC
        self.assertInvalid('RUC_EC', '1770012345001')    # tercer dígito 7
        bad_digit = CEDULA_OK[:9] + str((int(CEDULA_OK[9]) + 1) % 10)
        self.assertInvalid('RUC_EC', bad_digit + '001')

    def test_cedula_venezuela(self):
        self.assertEqual(normalize_identification('CEDULA_VE', 'v12.345.678'), 'V-12345678')
        self.assertEqual(normalize_identification('CEDULA_VE', '12345678'), 'V-12345678')
        self.assertEqual(normalize_identification('CEDULA_VE', 'E-84123456'), 'E-84123456')
        self.assertInvalid('CEDULA_VE', 'X-12345678')
        self.assertInvalid('CEDULA_VE', 'V-123')
        self.assertInvalid('CEDULA_VE', 'V-123456789')

    def test_cedula_colombia(self):
        self.assertEqual(normalize_identification('CEDULA_CO', '1.020.345.678'), '1020345678')
        self.assertEqual(normalize_identification('CEDULA_CO', '79123456'), '79123456')
        self.assertInvalid('CEDULA_CO', '12345')
        self.assertInvalid('CEDULA_CO', '01234567')
        self.assertInvalid('CEDULA_CO', '12345678901')
        self.assertInvalid('CEDULA_CO', '12A45678')


class CustomerCreateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(username='u', password='x')
        self.client.force_authenticate(user)

    def post(self, **extra):
        data = {'first_name': 'Ana', 'last_name': 'Paz', 'phone': '0999999999', **extra}
        return self.client.post('/customers/api/create/', data, format='json')

    def test_creates_venezuelan_customer_normalized(self):
        res = self.post(id_type='CEDULA_VE', cedula='v 12.345.678')
        self.assertEqual(res.status_code, 201, res.data)
        customer = Customer.objects.get(pk=res.data['id'])
        self.assertEqual(customer.cedula, 'V-12345678')
        self.assertEqual(customer.id_label, 'C.I. VE')

    def test_rejects_invalid_document(self):
        res = self.post(id_type='RUC_EC', cedula='123')
        self.assertEqual(res.status_code, 400)
        self.assertIn('13 dígitos', res.data['error'])

    def test_rejects_duplicate_document(self):
        self.assertEqual(self.post(id_type='CEDULA_CO', cedula='79123456').status_code, 201)
        res = self.post(id_type='CEDULA_CO', cedula='79.123.456')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Ya existe', res.data['error'])

    def test_same_number_allowed_for_different_country(self):
        self.assertEqual(self.post(id_type='CEDULA_CO', cedula=CEDULA_OK).status_code, 201)
        self.assertEqual(self.post(id_type='CEDULA_EC', cedula=CEDULA_OK).status_code, 201)

    def test_empty_document_and_default_type(self):
        self.assertEqual(self.post(cedula='').status_code, 201)
        self.assertEqual(self.post().status_code, 201)
        res = self.post(cedula=CEDULA_OK)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Customer.objects.get(pk=res.data['id']).id_type, 'CEDULA_EC')

    def test_invalid_type(self):
        self.assertEqual(self.post(id_type='PASAPORTE', cedula='123456').status_code, 400)
