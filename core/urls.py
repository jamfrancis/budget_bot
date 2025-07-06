from django.urls import path
from . import views, api_views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-account/', views.add_account, name='add_account'),
    path('edit-account/', views.edit_account, name='edit_account'),
    path('delete-accounts/', views.delete_accounts, name='delete_accounts'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    
    # Plaid integration endpoints
    path('plaid/create-link-token/', views.plaid_create_link_token, name='plaid_create_link_token'),
    path('plaid/exchange-token/', views.plaid_exchange_token, name='plaid_exchange_token'),
    path('plaid/update-balances/', views.plaid_update_balances, name='plaid_update_balances'),
    path('plaid/webhook/', views.plaid_webhook, name='plaid_webhook'),
    path('plaid/sync-transactions/', views.plaid_sync_transactions, name='plaid_sync_transactions'),
    
    # Chat API endpoints
    path('api/conversations/', api_views.ConversationListCreateView.as_view(), name='conversation_list_create'),
    path('api/conversations/<int:pk>/', api_views.ConversationDetailView.as_view(), name='conversation_detail'),
    path('api/conversations/<int:conversation_id>/messages/', api_views.ConversationMessagesView.as_view(), name='conversation_messages'),
    path('api/conversations/<int:conversation_id>/send/', api_views.send_message, name='send_message'),
    path('api/conversations/<int:conversation_id>/title/', api_views.update_conversation_title, name='update_conversation_title'),
]