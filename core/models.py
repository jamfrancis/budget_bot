# django imports for database models and user authentication
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


# stores plaid access tokens for each user
class PlaidToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # link to django user
    access_token = models.CharField(max_length=128)  # plaid access token
    item_id = models.CharField(max_length=128, blank=True, null=True)  # plaid item id
    cursor = models.CharField(max_length=255, blank=True, null=True)  # sync cursor for incremental updates
    created_at = models.DateTimeField(auto_now_add=True)  # when token was created
    updated_at = models.DateTimeField(auto_now=True)  # when token was last updated

    def __str__(self):
        return f"Plaid Token for {self.user.username}"


# represents bank accounts - can be manual or from plaid
class Account(models.Model):
    # predefined account types for dropdown selection
    ACCOUNT_TYPES = (
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit', 'Credit Card'),
        ('investment', 'Investment'),
        ('loan', 'Loan'),
        ('other', 'Other'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # account owner
    name = models.CharField(max_length=255)  # account name or bank name
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='other')  # type of account
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))  # current balance
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # available balance
    currency_code = models.CharField(max_length=3, default='USD')  # currency type
    
    # plaid specific fields (optional for manual accounts)
    plaid_account_id = models.CharField(max_length=255, blank=True, null=True, unique=True)  # plaid account identifier
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name}: ${self.balance}"

    @property
    def is_plaid_connected(self):
        return bool(self.plaid_account_id)


# individual financial transactions
class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)  # which account this transaction belongs to
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # transaction amount (negative for expenses)
    description = models.CharField(max_length=500)  # what the transaction was for
    date = models.DateField()  # when transaction occurred
    category = models.CharField(max_length=255, blank=True, null=True)  # spending category
    merchant_name = models.CharField(max_length=255, blank=True, null=True)  # store or merchant name
    
    # plaid specific fields (optional for manual transactions)
    plaid_transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)  # plaid transaction identifier
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.description}: ${self.amount}"

    @property
    def is_plaid_transaction(self):
        return bool(self.plaid_transaction_id)


# conversation containers for organizing chat history
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # conversation owner
    title = models.CharField(max_length=200)  # conversation title
    created_at = models.DateTimeField(auto_now_add=True)  # when conversation started
    updated_at = models.DateTimeField(auto_now=True)  # when last message was sent

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"


# individual messages within conversations
class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)  # which conversation
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)  # who sent the message
    content = models.TextField()  # message content
    timestamp = models.DateTimeField(auto_now_add=True)  # when message was sent

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


# legacy model - keeping for backward compatibility during migration
class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # which user's chat session
    question = models.TextField()  # user's question
    response = models.TextField()  # ai assistant's response
    created_at = models.DateTimeField(auto_now_add=True)  # when message was sent

    class Meta:
        ordering = ['-created_at']
