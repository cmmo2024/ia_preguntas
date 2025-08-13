from django.test import TestCase

# Create your tests here.
from django.contrib.auth.models import User
from .models import UserProfile, PlanConfig

class RequestLimitTest(TestCase):
    def setUp(self):
        # Crear usuario y perfil
        self.user = User.objects.create_user(username='testuser', password='123')
        self.profile = self.user.userprofile

    def test_free_user_can_request(self):
        config = PlanConfig.objects.create(plan='free', daily_requests=3)
        self.profile.daily_requests = 2
        self.assertTrue(self.profile.can_make_request())

    def test_free_user_reaches_limit(self):
        self.profile.daily_requests = 3
        self.assertFalse(self.profile.can_make_request())

    def test_premium_user_can_request(self):
        PlanConfig.objects.create(plan='premium', total_requests=300)
        self.profile.plan = 'premium'
        self.profile.total_requests = 299
        self.assertTrue(self.profile.can_make_request())

    def test_premium_user_exceeds_limit_resets_to_free(self):
        PlanConfig.objects.create(plan='premium', total_requests=300)
        self.profile.plan = 'premium'
        self.profile.total_requests = 300
        self.assertFalse(self.profile.can_make_request())
        self.assertEqual(self.profile.plan, 'free')  # Debe haberse reseteado