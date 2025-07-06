# plaid api imports for banking integration
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.configuration import Configuration, Environment
from plaid.api_client import ApiClient
# django and python imports
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# main service class for plaid banking integration
class PlaidService:
    def __init__(self):
        # map environment names to plaid api urls
        env_mapping = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com', 
            'production': 'https://production.plaid.com',
        }
        host = env_mapping.get(settings.PLAID_ENV, 'https://sandbox.plaid.com')  # default to sandbox
        
        # configure plaid client with credentials
        configuration = Configuration(
            host=host,
            api_key={
                'clientId': settings.PLAID_CLIENT_ID,
                'secret': settings.PLAID_SECRET,
            }
        )
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)  # main plaid api client

    # creates a link token for plaid link initialization
    def create_link_token(self, user_id):
        # build request with required parameters
        request = LinkTokenCreateRequest(
            products=[Products('transactions')],  # we want transaction data
            client_name="Balai Budget App",  # app name shown to user
            country_codes=[CountryCode('US')],  # us banks only
            language='en',  # english interface
            user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),  # unique user identifier
        )
        try:
            response = self.client.link_token_create(request)
            return response['link_token']  # return token for frontend
        except Exception as e:
            logger.error(f"Error creating link token: {e}")
            raise

    # exchanges public token for access token after plaid link success
    def exchange_public_token(self, public_token):
        request = ItemPublicTokenExchangeRequest(public_token=public_token)  # token from frontend
        try:
            response = self.client.item_public_token_exchange(request)
            return response['access_token']  # permanent access token for api calls
        except Exception as e:
            logger.error(f"Error exchanging public token: {e}")
            raise

    # fetches all bank accounts for a user
    def get_accounts(self, access_token):
        request = AccountsGetRequest(access_token=access_token)  # use stored access token
        try:
            response = self.client.accounts_get(request)
            return response['accounts']  # list of account objects
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            raise

    # fetches transactions for a date range
    def get_transactions(self, access_token, start_date=None, end_date=None):
        # default to last 30 days if no dates provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date.date(),  # convert to date object
            end_date=end_date.date()
        )
        try:
            response = self.client.transactions_get(request)
            transactions = response['transactions']
            logger.info(f"Fetched {len(transactions)} transactions from Plaid")
            return transactions  # list of transaction objects
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            raise

    # syncs plaid accounts to our database
    def sync_accounts(self, user, access_token):
        from core.models import Account
        
        try:
            accounts = self.get_accounts(access_token)  # fetch from plaid
            created_accounts = []
            
            # create or update each account in our database
            for account_data in accounts:
                account, created = Account.objects.update_or_create(
                    plaid_account_id=account_data['account_id'],  # unique plaid identifier
                    defaults={
                        'user': user,  # link to our user
                        'name': account_data['name'],  # bank account name
                        'account_type': self._map_account_type(account_data['type']),  # convert plaid type
                        'balance': Decimal(str(account_data['balances']['current'] or 0)),  # current balance
                        'available_balance': Decimal(str(account_data['balances']['available'] or 0)) if account_data['balances']['available'] else None,  # available balance
                        'currency_code': account_data['balances']['iso_currency_code'] or 'USD',  # currency
                    }
                )
                created_accounts.append(account)
            
            return created_accounts
        except Exception as e:
            logger.error(f"Error syncing accounts: {e}")
            raise

    # syncs plaid transactions to our database
    def sync_transactions(self, user, access_token):
        from core.models import Transaction, Account
        
        try:
            transactions = self.get_transactions(access_token)  # fetch from plaid
            created_transactions = []
            
            # create or update each transaction in our database
            for transaction_data in transactions:
                try:
                    # find the account this transaction belongs to
                    account = Account.objects.get(
                        plaid_account_id=transaction_data['account_id'],
                        user=user
                    )
                    
                    # create or update transaction
                    transaction, created = Transaction.objects.update_or_create(
                        plaid_transaction_id=transaction_data['transaction_id'],  # unique plaid identifier
                        defaults={
                            'account': account,  # link to our account
                            'amount': -Decimal(str(transaction_data['amount'])),  # plaid amounts are positive for debits, so negate them
                            'date': transaction_data['date'],  # transaction date
                            'description': transaction_data['name'],  # transaction description
                            'merchant_name': transaction_data.get('merchant_name'),  # merchant if available
                            'category': self._safe_join_categories(transaction_data.get('category')),  # join categories safely
                        }
                    )
                    created_transactions.append(transaction)
                except Account.DoesNotExist:
                    logger.warning(f"Account not found for transaction {transaction_data['transaction_id']}")
                    continue  # skip this transaction
            
            return created_transactions
        except Exception as e:
            logger.error(f"Error syncing transactions: {e}")
            raise

    # gets real-time account balances (more current than regular accounts endpoint)
    def get_real_time_balances(self, access_token):
        request = AccountsBalanceGetRequest(access_token=access_token)  # use stored access token
        try:
            response = self.client.accounts_balance_get(request)
            return response['accounts']  # list of accounts with current balances
        except Exception as e:
            logger.error(f"Error fetching real-time balances: {e}")
            raise

    # incremental sync only fetches new/changed transactions since last sync
    def sync_transactions_incremental(self, access_token, cursor=None):
        request = TransactionsSyncRequest(access_token=access_token)  # use stored access token
        if cursor:
            request.cursor = cursor  # resume from where we left off
            
        try:
            response = self.client.transactions_sync(request)
            return {
                'added': response.get('added', []),  # new transactions
                'modified': response.get('modified', []),  # changed transactions
                'removed': response.get('removed', []),  # deleted transactions
                'next_cursor': response.get('next_cursor'),  # bookmark for next sync
                'has_more': response.get('has_more', False)  # more data available
            }
        except Exception as e:
            logger.error(f"Error in incremental transaction sync: {e}")
            raise

    # updates our stored account balances with real-time data from plaid
    def update_account_balances(self, user, access_token):
        from core.models import Account
        
        try:
            accounts_data = self.get_real_time_balances(access_token)  # fetch latest balances
            updated_accounts = []
            
            # update each account's balance in our database
            for account_data in accounts_data:
                try:
                    # find the account in our database
                    account = Account.objects.get(
                        plaid_account_id=account_data['account_id'],
                        user=user
                    )
                    # update balance fields
                    account.balance = Decimal(str(account_data['balances']['current'] or 0))
                    if account_data['balances']['available']:
                        account.available_balance = Decimal(str(account_data['balances']['available']))
                    account.save()  # save to database
                    updated_accounts.append(account)
                except Account.DoesNotExist:
                    logger.warning(f"Account not found for balance update: {account_data['account_id']}")
                    continue  # skip this account
            
            return updated_accounts
        except Exception as e:
            logger.error(f"Error updating account balances: {e}")
            raise

    # maps plaid account types to our internal account types
    def _map_account_type(self, plaid_type):
        # convert enum to string if needed
        if hasattr(plaid_type, 'value'):
            plaid_type = plaid_type.value
        elif not isinstance(plaid_type, str):
            plaid_type = str(plaid_type)
            
        # conversion table from plaid types to our types
        mapping = {
            'depository': 'checking',  # checking and savings accounts
            'credit': 'credit',  # credit cards
            'loan': 'loan',  # loans and mortgages
            'investment': 'investment',  # investment accounts
        }
        return mapping.get(plaid_type, 'other')  # default to other if unknown
    
    # safely join categories list
    def _safe_join_categories(self, categories):
        if not categories:
            return ''
        if isinstance(categories, list):
            return ', '.join(str(cat) for cat in categories)
        return str(categories)