import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.models import LoanDocument


@login_required
def loan_document_list(request):
    documents = list(
        LoanDocument.objects.select_related(
            "loan",
            "loan__member",
            "loan__loan_type",
            "uploaded_by",
        )
        .filter(loan__status__in=["approved", "disbursed"])
        .order_by("-created_at", "-id")
    )

    approved_documents = 0
    active_documents = 0
    loans_with_documents = set()

    for document in documents:
        document.file_name = os.path.basename(document.file.name)
        document.uploaded_by_display = (
            document.uploaded_by.get_full_name() if document.uploaded_by else ""
        ) or getattr(document.uploaded_by, "username", "—")
        loans_with_documents.add(document.loan_id)

        if document.loan.status == "approved":
            approved_documents += 1
        elif document.loan.status == "disbursed":
            active_documents += 1

    return render(
        request,
        "loan/loan_document_list.html",
        {
            "segment": "loan_documents",
            "documents": documents,
            "kpi_total_documents": len(documents),
            "kpi_loans_with_documents": len(loans_with_documents),
            "kpi_approved_documents": approved_documents,
            "kpi_active_documents": active_documents,
        },
    )
