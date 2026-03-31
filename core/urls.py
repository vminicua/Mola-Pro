from django.urls import path
from core.views.dashboard_view import dashboard_view
from core.views.member.member_view import add_member, member_list, update_member, deactivate_member, member_detail_json
from core.views.account.account_view import account_type_list, create_account_type, update_account_type, toggle_account_type_status
from core.views.account.account_view import client_account_list, create_client_account, update_client_account, toggle_client_account_status
from core.views.account.account_view import company_account_list, create_company_account, update_company_account, deactivate_company_account
from core.views.expense.expense_view import expense_category_list, create_expense_category
from core.views.expense.expense_view import expense_list, create_expense, download_expense_attachment, update_expense_category, deactivate_expense_category
from core.views.income.income_view import income_category_list, create_income_category, income_list, create_income, download_income_attachment, update_income_category, toggle_income_category_status
from core.views.transaction.transaction_view import transaction_list
from core.views.interest.interest_view import interest_type_list, create_interest_type, interest_calculator, update_interest_type, toggle_interest_type_status
from core.views.loan.loan_views import new_loan
from core.views.loan.loan_type_views import loan_type_list, create_loan_type, update_loan_type, toggle_loan_type
from core.views.loan.loan_views import pending_loans_list, confirm_loan, reject_loan
from core.views.payments.loan_disbursement_views import loan_disbursement_list, register_disbursement
from core.views.loan.active_loan import active_loans_list, active_loan_details
from core.views.payments.loan_repayment_views import loan_repayment_list, register_repayment
from core.views.loan.all_loan_list_views import loan_list_all, loan_details_any_status
from core.views.user.user_views import user_list, toggle_user_active, update_user_groups, create_user,update_user
from core.views.reports.report_views import report_filters, generate_report_pdf
from core.views.preferences_view import preferences_view, update_brand_preferences

app_name = "core"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("members/add/", add_member, name="add_member"),
    path("members/list/", member_list, name="member_list"),
    path("members/<int:member_id>/update/", update_member, name="update_member"),
    path("members/<int:member_id>/deactivate/", deactivate_member, name="deactivate_member"),
    path("members/<int:member_id>/detail-json/", member_detail_json, name="member_detail_json"),
    
    
    
    # Tipos de Contas
    path("accounts/types/", account_type_list, name="account_type_list"),
    path("accounts/types/create/", create_account_type, name="create_account_type"),
    path("accounts/types/update/",update_account_type,name="update_account_type",),
    path("accounts/types/toggle-status/",toggle_account_type_status,name="toggle_account_type_status",),

    
        # Contas do Cliente
    path("accounts/client/", client_account_list, name="client_account_list"),
    path("accounts/client/create/", create_client_account, name="create_client_account"),
    path("accounts/client/update/",update_client_account,name="update_client_account",),
    path("accounts/client/toggle-status/",toggle_client_account_status,name="toggle_client_account_status",),


    # Contas da Empresa
    path("accounts/company/", company_account_list, name="company_account_list"),
    path("accounts/company/create/", create_company_account, name="create_company_account"),
    path("accounts/company/<int:account_id>/update/", update_company_account, name="update_company_account"),
    path("accounts/company/<int:account_id>/deactivate/", deactivate_company_account, name="deactivate_company_account"),
    
    path("expenses/categories/", expense_category_list, name="expense_category_list"),
    path("expenses/categories/create/", create_expense_category, name="create_expense_category"),
    path("expenses/", expense_list, name="expense_list"),
    path("expenses/create/", create_expense, name="create_expense"),
    path("expenses/<int:expense_id>/download/", download_expense_attachment, name="download_expense_attachment"),
    path("expenses/categories/update/",update_expense_category,name="update_expense_category",),
    path("expenses/categories/deactivate/",deactivate_expense_category,name="deactivate_expense_category",),

     
     
     # Rendimentos - Tipos
    path("incomes/categories/", income_category_list, name="income_category_list"),
    path("incomes/categories/create/", create_income_category, name="create_income_category"),
    path("incomes/categories/update/", update_income_category,name="update_income_category",),
    path("incomes/categories/toggle-status/",toggle_income_category_status,name="toggle_income_category_status",),


    # Rendimentos - Lançamentos
    path("incomes/", income_list, name="income_list"),
    path("incomes/create/", create_income, name="create_income"),
    path("incomes/<int:income_id>/download/", download_income_attachment, name="download_income_attachment"),
    
    
    # Transações
    path("transactions/", transaction_list, name="transaction_list"),
    
    
    # Juros
    path("interest/types/", interest_type_list, name="interest_type_list"),
    path("interest/types/create/", create_interest_type, name="create_interest_type"),
    path("interest/calculator/", interest_calculator, name="interest_calculator"),
    path("interest/types/update/", update_interest_type,name="update_interest_type",),
    path("interest/types/toggle-status/", toggle_interest_type_status,name="toggle_interest_type_status",),

    
    
    path("loans/new/", new_loan, name="new_loan"),
    
    
        # Tipos de Empréstimos
    path("loan-types/", loan_type_list, name="loan_type_list"),
    path("loan-types/create/", create_loan_type, name="create_loan_type"),
    path("loan-types/<int:type_id>/update/", update_loan_type, name="update_loan_type"),
    path("loan-types/<int:type_id>/toggle/", toggle_loan_type, name="toggle_loan_type"),
    
    path("loans/pending/", pending_loans_list, name="pending_loans"),
    path("loans/<int:loan_id>/confirm/", confirm_loan, name="confirm_loan"),
    path("loans/<int:loan_id>/reject/", reject_loan, name="reject_loan"),
    
    path("loans/active/", active_loans_list, name="active_loans_list"),
     path("loans/active/<int:loan_id>/details/", active_loan_details, name="active_loan_details"),
     
     path("loans/all/", loan_list_all, name="loan_list_all"),
     path("loans/<int:loan_id>/details/", loan_details_any_status, name="loan_details_any_status",),


    path("loans/disbursement/", loan_disbursement_list, name="loan_disbursement_list"),
    path("loans/<int:loan_id>/disburse/", register_disbursement, name="register_disbursement"),
    path("loans/repayments/", loan_repayment_list, name="loan_repayment_list"),
    path("loans/<int:loan_id>/repay/", register_repayment, name="register_repayment"),
    
    # UTILIZADORES
    path("users/", user_list, name="user_list"),
    path("users/create/", create_user, name="create_user"),
    path("users/<int:user_id>/toggle-active/", toggle_user_active, name="toggle_user_active"),
    path("users/<int:user_id>/update-groups/", update_user_groups, name="update_user_groups"),
    path("users/<int:user_id>/update/", update_user, name="update_user"),

    # PREFERÊNCIAS
    path("preferences/", preferences_view, name="preferences"),
    path("preferences/branding/update/", update_brand_preferences, name="update_brand_preferences"),

    # RELATÓRIOS
    path("reports/", report_filters, name="report_filters"),
    path("reports/pdf/", generate_report_pdf, name="generate_report_pdf"),

]
