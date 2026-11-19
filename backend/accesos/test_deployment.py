from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accesos.models import CuentaSistema, OperadorSistema


@override_settings(
    DEBUG=False, ALLOWED_HOSTS=['api.example.test'],
    CSRF_TRUSTED_ORIGINS=['https://demo.example.test'],
    SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
)
class DeploymentTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('operator', password='A-test-password-918!')
        person = OperadorSistema.objects.create(
            nombre='Demo', apellido='Operador', dni=9191, email='demo@example.test',
            username='operator', password_hash='', turno_asignado='Mañana',
        )
        CuentaSistema.objects.create(usuario=user, persona=person, rol='Operador')
        self.client = APIClient(enforce_csrf_checks=True)
        self.headers = {
            'HTTP_HOST': 'api.example.test', 'HTTP_ORIGIN': 'https://demo.example.test',
            'HTTP_X_FORWARDED_PROTO': 'https',
        }

    def test_proxy_csrf_session_rotation_logout(self):
        response = self.client.get('/api/auth/csrf/', **self.headers)
        self.assertEqual(response.status_code, 200)
        csrf = self.client.cookies['csrftoken']
        self.assertTrue(csrf['secure'])
        self.assertFalse(csrf['domain'])
        self.assertEqual(csrf['samesite'], 'Lax')
        old_token = csrf.value
        data = {'username': 'operator', 'password': 'A-test-password-918!'}
        self.assertEqual(self.client.post('/api/auth/login/', data, format='json', **self.headers).status_code, 403)
        response = self.client.post('/api/auth/login/', data, format='json', HTTP_X_CSRFTOKEN=old_token, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        session = self.client.cookies['sessionid']
        self.assertTrue(session['secure'])
        self.assertTrue(session['httponly'])
        self.assertFalse(session['domain'])
        self.assertNotEqual(old_token, self.client.cookies['csrftoken'].value)
        self.assertEqual(self.client.get('/api/auth/me/', **self.headers).json()['rol'], 'Operador')
        token = self.client.cookies['csrftoken'].value
        bad_origin = {**self.headers, 'HTTP_ORIGIN': 'https://attacker.example.test'}
        self.assertEqual(self.client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=token, **bad_origin).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=token, **self.headers).status_code, 204)
        self.assertEqual(self.client.get('/api/auth/me/', **self.headers).status_code, 401)

    def test_health_does_not_expose_details(self):
        response = self.client.get('/api/health/', **self.headers)
        self.assertEqual(response.json(), {'status': 'ok'})
        from django.db import DatabaseError
        with patch('sgca_backend.deployment.connection.cursor', side_effect=DatabaseError('secret')):
            response = self.client.get('/api/health/', **self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})

    def test_existing_database_is_not_seeded(self):
        with self.assertRaises(CommandError):
            call_command('crear_demo_segura', confirm_empty=True, stdout=StringIO())

    def test_production_seed_requires_new_passwords(self):
        with patch.dict('os.environ', {'APL_DEMO_OPERATOR_PASSWORD': '', 'APL_DEMO_TECH_PASSWORD': ''}):
            with self.assertRaises(CommandError):
                call_command('seed_demo', stdout=StringIO())
