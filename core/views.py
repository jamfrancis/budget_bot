# django imports for views and http responses
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal
import json

# our models and services
from .models import Account, Transaction, ChatMessage, PlaidToken
from .forms import ChatForm
from .services.llm import LLMService
from .services.plaid import PlaidService


# main homepage - shows modern chat interface
def home(request):
    # redirect to login if not authenticated
    if not request.user.is_authenticated:
        return redirect('admin:login')
    
    # render the new chat interface
    return render(request, 'core/chat_v2.html')


# dashboard shows accounts and transactions overview
@login_required
def dashboard(request):
    # get user's accounts and transactions
    accounts = Account.objects.filter(user=request.user)
    recent_transactions = Transaction.objects.filter(account__user=request.user).order_by('-date', '-created_at')[:10]
    
    # calculate total balance (only checking, savings, credit cards - exclude investments and loans)
    liquid_accounts = accounts.filter(account_type__in=['checking', 'savings', 'credit'])
    total_balance = 0
    for account in liquid_accounts:
        if account.account_type == 'credit':
            total_balance -= account.balance  # subtract credit card debt
        else:
            total_balance += account.balance  # add checking/savings
    
    return render(request, 'core/dashboard.html', {
        'accounts': accounts,
        'recent_transactions': recent_transactions,
        'total_balance': total_balance
    })


# allows manual addition of bank accounts
@login_required
def add_account(request):
    if request.method == 'POST':
        name = request.POST.get('name')  # account name from form
        balance = request.POST.get('balance', '0.00')  # starting balance
        
        if name:
            # create new account for this user
            Account.objects.create(
                user=request.user,
                name=name,
                account_type=request.POST.get('account_type', 'other'),
                balance=Decimal(balance)
            )
            messages.success(request, f'Account "{name}" added successfully!')
        
    return redirect('dashboard')  # go back to dashboard


# allows editing of existing accounts
@login_required
def edit_account(request):
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        name = request.POST.get('name')
        account_type = request.POST.get('account_type')
        balance = request.POST.get('balance')
        
        try:
            # find the account (must belong to current user)
            account = Account.objects.get(id=account_id, user=request.user)
            
            # update account fields
            account.name = name
            account.account_type = account_type
            account.balance = Decimal(balance)
            account.save()
            
            messages.success(request, f'Account "{name}" updated successfully!')
        except Account.DoesNotExist:
            messages.error(request, 'Account not found.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid balance amount.')
    
    return redirect('dashboard')  # go back to dashboard


# allows manual addition of transactions
@login_required
def add_transaction(request):
    if request.method == 'POST':
        account_id = request.POST.get('account')  # which account
        amount = request.POST.get('amount')  # transaction amount
        description = request.POST.get('description')  # what it was for
        
        try:
            # find the account (must belong to current user)
            account = Account.objects.get(id=account_id, user=request.user)
            
            # create the transaction
            from datetime import date
            Transaction.objects.create(
                account=account,
                amount=Decimal(amount),
                description=description,
                date=date.today()  # use today's date for manual transactions
            )
            
            # update account balance
            account.balance += Decimal(amount)
            account.save()
            
            messages.success(request, 'Transaction added successfully!')
        except Account.DoesNotExist:
            messages.error(request, 'Account not found.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid amount.')
    
    return redirect('dashboard')  # go back to dashboard


# creates plaid link token for bank account connection
@login_required
def plaid_create_link_token(request):
    if request.method == 'POST':
        try:
            plaid_service = PlaidService()
            link_token = plaid_service.create_link_token(request.user.id)  # create token for this user
            return JsonResponse({'link_token': link_token})  # return token to frontend
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# exchanges public token for access token after plaid link success
@login_required
@require_POST
def plaid_exchange_token(request):
    try:
        data = json.loads(request.body)  # parse json from frontend
        public_token = data.get('public_token')  # token from plaid link
        
        if not public_token:
            return JsonResponse({'error': 'No public token provided'}, status=400)
        
        plaid_service = PlaidService()
        access_token = plaid_service.exchange_public_token(public_token)  # get permanent token
        
        # save access token in database
        plaid_token, created = PlaidToken.objects.get_or_create(user=request.user)
        plaid_token.access_token = access_token
        plaid_token.save()
        
        # sync initial data from plaid
        plaid_service.sync_accounts(request.user, access_token)  # get accounts
        
        # wait a moment for transactions to be ready, then try to sync
        import time
        time.sleep(2)
        try:
            plaid_service.sync_transactions(request.user, access_token)  # get transactions
        except Exception as e:
            # transactions might not be ready yet, that's ok
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Transactions not ready yet: {e}")
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# updates account balances with real-time data from plaid
@login_required
@require_POST
def plaid_update_balances(request):
    try:
        plaid_token = PlaidToken.objects.get(user=request.user)  # get user's plaid token
        plaid_service = PlaidService()
        
        # update balances for all user's plaid accounts
        updated_accounts = plaid_service.update_account_balances(
            request.user, 
            plaid_token.access_token
        )
        
        return JsonResponse({
            'success': True,
            'updated_count': len(updated_accounts)  # how many accounts updated
        })
    except PlaidToken.DoesNotExist:
        return JsonResponse({'error': 'No Plaid token found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# handles webhook notifications from plaid for automatic updates
@csrf_exempt
@require_POST
def plaid_webhook(request):
    try:
        data = json.loads(request.body)  # parse webhook data
        webhook_type = data.get('webhook_type')  # type of webhook
        webhook_code = data.get('webhook_code')  # specific event
        item_id = data.get('item_id')  # plaid item identifier
        
        # handle transaction update webhooks
        if webhook_type == 'TRANSACTIONS':
            if webhook_code in ['SYNC_UPDATES_AVAILABLE', 'DEFAULT_UPDATE']:
                # find user with this item_id and sync transactions
                try:
                    plaid_token = PlaidToken.objects.get(item_id=item_id)
                    plaid_service = PlaidService()
                    
                    # perform incremental sync (only new/changed transactions)
                    sync_result = plaid_service.sync_transactions_incremental(
                        plaid_token.access_token,
                        plaid_token.cursor  # resume from last sync point
                    )
                    
                    # update cursor for next sync
                    plaid_token.cursor = sync_result['next_cursor']
                    plaid_token.save()
                    
                    # update balances after transaction sync
                    plaid_service.update_account_balances(
                        plaid_token.user,
                        plaid_token.access_token
                    )
                    
                except PlaidToken.DoesNotExist:
                    pass  # token not found, ignore webhook
        
        return JsonResponse({'acknowledged': True})  # acknowledge webhook
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)# manually sync transactions for testing
@login_required
@require_POST
def plaid_sync_transactions(request):
    try:
        plaid_token = PlaidToken.objects.get(user=request.user)
        plaid_service = PlaidService()
        
        transactions = plaid_service.sync_transactions(
            request.user, 
            plaid_token.access_token
        )
        
        return JsonResponse({
            'success': True,
            'synced_count': len(transactions)
        })
    except PlaidToken.DoesNotExist:
        return JsonResponse({'error': 'No Plaid token found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# delete multiple accounts
@login_required
@require_POST
def delete_accounts(request):
    try:
        data = json.loads(request.body)
        account_ids = data.get('account_ids', [])
        
        if not account_ids:
            return JsonResponse({'error': 'No accounts selected'}, status=400)
        
        # delete accounts that belong to the current user
        deleted_count = Account.objects.filter(
            id__in=account_ids,
            user=request.user
        ).delete()[0]
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)