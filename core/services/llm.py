# anthropic claude api integration
import anthropic
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

logger = logging.getLogger(__name__)


# service class for claude ai financial assistant integration
class LLMService:
    def __init__(self):
        # initialize claude client with api key from settings
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # builds context-aware prompt with user's financial data
    def build_financial_context(self, user):
        from core.models import Account, Transaction
        
        # get user's account balances for context
        accounts = Account.objects.filter(user=user).values('name', 'balance', 'account_type')
        
        # get recent transactions (limit to 50 for token efficiency)
        recent_transactions = Transaction.objects.filter(
            account__user=user
        ).order_by('-date')[:50].values('date', 'description', 'amount', 'category')
        
        # build structured context as json for claude
        context_data = {
            'balances': list(accounts),
            'recent_transactions': list(recent_transactions),
            'total_balance': sum(acc['balance'] for acc in accounts)
        }
        
        return json.dumps(context_data, default=str)

    # builds complete message array for claude api
    def build_messages(self, user, question):
        # get financial context as json
        context_json = self.build_financial_context(user)
        
        return [
            {
                "role": "user",
                "content": f"USER_CONTEXT:\n{context_json}\n\nQUESTION: {question}"
            }
        ]
    
    # main method to get financial advice from claude
    def get_response(self, message, user):
        return self.get_financial_advice(message, user)
    
    def get_financial_advice(self, user_question, user):
        # check if api key is properly configured
        if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == 'your-anthropic-api-key-here':
            return f"Hi! I'm bal.ai, your financial assistant. I'd love to help with your question: '{user_question}'\n\nHowever, I need an Anthropic API key to provide personalized advice. Please set up your API key at https://console.anthropic.com/account/keys and add it to your .env file.\n\nOnce configured, I'll be able to analyze your financial data and provide tailored recommendations!"
        
        try:
            # build messages with financial context
            messages = self.build_messages(user, user_question)
            
            # call claude api with structured messages
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # use haiku model for faster/cheaper responses
                max_tokens=600,  # increased for better responses
                temperature=0.7,  # slight creativity for natural responses
                system="You are bal.ai, a personal finance assistant. Use the provided JSON context to answer questions precisely. Be helpful, concise, and practical.",
                messages=messages,
                # add user metadata for tracking and security
                metadata={"user_id": str(user.id)}
            )
            
            # log token usage for cost tracking
            if hasattr(response, 'usage'):
                logger.info(f"Claude API usage - Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error getting financial advice: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again later."