from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import UserProfile, Account, Transaction, Goal
from .services.llm import LLMService


class LLMServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user_profile = UserProfile.objects.create(user=self.user, monthly_income=Decimal('5000.00'))
        
        self.account = Account.objects.create(
            user=self.user,
            plaid_account_id='test_account_id',
            name='Test Checking',
            account_type='checking',
            current_balance=Decimal('1500.00')
        )
        
        self.goal = Goal.objects.create(
            user=self.user,
            title='Emergency Fund',
            goal_type='emergency',
            target_amount=Decimal('5000.00'),
            current_amount=Decimal('1000.00')
        )

    def test_build_prompt(self):
        llm_service = LLMService()
        prompt = llm_service.build_prompt("Can I afford a $500 vacation?", self.user)
        
        self.assertIn("Can I afford a $500 vacation?", prompt)
        self.assertIn("Test Checking: $1,500.00", prompt)
        self.assertIn("Emergency Fund", prompt)

    @patch('anthropic.Anthropic')
    def test_get_financial_advice(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Based on your current balance, you can afford the vacation."
        mock_client.messages.create.return_value = mock_response
        
        llm_service = LLMService()
        advice = llm_service.get_financial_advice("Can I afford a $500 vacation?", self.user)
        
        self.assertEqual(advice, "Based on your current balance, you can afford the vacation.")


class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Balai')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_chat_post_integration(self):
        self.client.login(username='testuser', password='testpass')
        
        # Create some test data
        Account.objects.create(
            user=self.user,
            plaid_account_id='test_account',
            name='Test Account',
            account_type='checking',
            current_balance=Decimal('1000.00')
        )
        
        with patch('core.services.llm.LLMService.get_financial_advice') as mock_advice:
            mock_advice.return_value = "You have $1000 in your checking account."
            
            response = self.client.post(reverse('chat'), {
                'message': 'What is my balance?'
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'What is my balance?')
            self.assertContains(response, 'You have $1000 in your checking account.')


class ModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_goal_progress_percentage(self):
        goal = Goal.objects.create(
            user=self.user,
            title='Test Goal',
            goal_type='savings',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('250.00')
        )
        
        self.assertEqual(goal.progress_percentage, 25.0)

    def test_goal_remaining_amount(self):
        goal = Goal.objects.create(
            user=self.user,
            title='Test Goal',
            goal_type='savings',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('250.00')
        )
        
        self.assertEqual(goal.remaining_amount, Decimal('750.00'))

    def test_account_str_method(self):
        account = Account.objects.create(
            user=self.user,
            plaid_account_id='test_account',
            name='Test Checking',
            account_type='checking',
            current_balance=Decimal('1000.00')
        )
        
        self.assertEqual(str(account), 'Test Checking (Checking)')
