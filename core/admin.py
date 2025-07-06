from django.contrib import admin
from .models import PlaidToken, Account, Transaction, ChatMessage


@admin.register(PlaidToken)
class PlaidTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'item_id']
    readonly_fields = ['access_token', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'account_type', 'balance', 'is_plaid_connected', 'created_at']
    list_filter = ['account_type', 'created_at']
    search_fields = ['name', 'user__username', 'plaid_account_id']
    readonly_fields = ['plaid_account_id', 'created_at', 'updated_at']
    
    def is_plaid_connected(self, obj):
        return obj.is_plaid_connected
    is_plaid_connected.boolean = True
    is_plaid_connected.short_description = 'Plaid Connected'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'date', 'account', 'is_plaid_transaction']
    list_filter = ['date', 'account__account_type']
    search_fields = ['description', 'account__user__username', 'plaid_transaction_id']
    readonly_fields = ['plaid_transaction_id', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def is_plaid_transaction(self, obj):
        return obj.is_plaid_transaction
    is_plaid_transaction.boolean = True
    is_plaid_transaction.short_description = 'Plaid Transaction'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'question', 'response']
    readonly_fields = ['created_at']
    
    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')