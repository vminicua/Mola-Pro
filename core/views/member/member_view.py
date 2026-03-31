from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from core.models import Member, Loan
from django.urls import reverse
from django.http import JsonResponse
from datetime import datetime
from django.utils.translation import gettext as _


def add_member(request):
    User = get_user_model()
    gestores = User.objects.filter(is_active=True, is_superuser=False).order_by("first_name", "last_name")

    errors = {}
    form_data = {}

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        legal_name = request.POST.get("legal_name", "").strip()
        is_company = request.POST.get("is_company") == "on"
        phone = request.POST.get("phone", "").strip()
        alt_phone = request.POST.get("alt_phone", "").strip()
        email = request.POST.get("email", "").strip()
        city = request.POST.get("city", "").strip()
        address = request.POST.get("address", "").strip()
        profession = request.POST.get("profession", "").strip()
        marital_status = request.POST.get("marital_status", "").strip()
        gender = request.POST.get("gender", "").strip()
        manager_id = request.POST.get("manager", "").strip()

        # NOVO: NUIT (no add)
        nuit = request.POST.get("nuit", "").strip()

        form_data = {
            "first_name": first_name,
            "last_name": last_name,
            "legal_name": legal_name,
            "is_company": is_company,
            "phone": phone,
            "alt_phone": alt_phone,
            "email": email,
            "city": city,
            "address": address,
            "profession": profession,
            "marital_status": marital_status,
            "gender": gender,
            "manager": manager_id,
            "nuit": nuit,
        }

        if not first_name:
            errors["first_name"] = _("Nome é obrigatório.")
        if not last_name:
            errors["last_name"] = _("Apelido é obrigatório.")
        if not phone:
            errors["phone"] = _("Telefone é obrigatório.")
        if not manager_id:
            errors["manager"] = _("Selecione o gestor responsável.")

        manager = None
        if manager_id:
            try:
                manager = gestores.get(pk=manager_id)
            except User.DoesNotExist:
                errors["manager"] = _("Gestor inválido.")

        if not errors and manager is not None:
            Member.objects.create(
                first_name=first_name,
                last_name=last_name,
                legal_name=legal_name or None,
                is_company=is_company,
                phone=phone,
                alt_phone=alt_phone or None,
                email=email or None,
                city=city or None,
                address=address or None,
                profession=profession or None,
                marital_status=marital_status or None,
                gender=gender or None,
                manager=manager,
                nuit=nuit or None,  # NOVO
            )

            url = reverse("core:member_list")
            return redirect(f"{url}?created=1")

    return render(
        request,
        "member/add_member.html",
        {
            "gestores": gestores,
            "errors": errors,
            "form_data": form_data,
            "segment": "member_add",
        },
    )



#============================================================================================================
#============================================================================================================
def member_list(request):
    User = get_user_model()
    gestores = User.objects.filter(is_active=True, is_superuser=False).order_by("first_name", "last_name")
    members = (
        Member.objects.filter(is_active=True)
        .select_related("manager")
        .prefetch_related("loans")
        .order_by("-id")
    )
    return render(
        request,
        "member/list_members.html",
        {
            "members": members,
            "gestores": gestores,
            "segment": "members_list",
        },
    )


#============================================================================================================
#============================================================================================================
def update_member(request, member_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": _("Método inválido.")}, status=405)

    try:
        member = Member.objects.get(pk=member_id, is_active=True)
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Membro não encontrado.")}, status=404)

    User = get_user_model()
    gestores = User.objects.filter(is_active=True, is_superuser=False)

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    legal_name = request.POST.get("legal_name", "").strip()
    is_company = request.POST.get("is_company") == "on"
    phone = request.POST.get("phone", "").strip()
    alt_phone = request.POST.get("alt_phone", "").strip()
    email = request.POST.get("email", "").strip()
    city = request.POST.get("city", "").strip()
    address = request.POST.get("address", "").strip()
    profession = request.POST.get("profession", "").strip()
    marital_status = request.POST.get("marital_status", "").strip()
    gender = request.POST.get("gender", "").strip()
    manager_id = request.POST.get("manager", "").strip()

    # NOVO: NUIT + KYC
    nuit = request.POST.get("nuit", "").strip()
    id_type = request.POST.get("id_type", "").strip()
    id_number = request.POST.get("id_number", "").strip()
    id_issue_date_str = request.POST.get("id_issue_date", "").strip()
    id_expiry_date_str = request.POST.get("id_expiry_date", "").strip()
    kyc_notes = request.POST.get("kyc_notes", "").strip()

    if not first_name or not last_name or not phone or not manager_id:
        return JsonResponse(
            {
                "success": False,
                "message": _("Nome, apelido, telefone e gestor são obrigatórios."),
            },
            status=400,
        )

    try:
        manager = gestores.get(pk=manager_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Gestor inválido.")}, status=400)

    # Parse datas KYC (se vierem)
    id_issue_date = None
    if id_issue_date_str:
        try:
            id_issue_date = datetime.strptime(id_issue_date_str, "%Y-%m-%d").date()
        except ValueError:
            id_issue_date = None

    id_expiry_date = None
    if id_expiry_date_str:
        try:
            id_expiry_date = datetime.strptime(id_expiry_date_str, "%Y-%m-%d").date()
        except ValueError:
            id_expiry_date = None

    member.first_name = first_name
    member.last_name = last_name
    member.legal_name = legal_name or None
    member.is_company = is_company
    member.phone = phone
    member.alt_phone = alt_phone or None
    member.email = email or None
    member.city = city or None
    member.address = address or None
    member.profession = profession or None
    member.marital_status = marital_status or None
    member.gender = gender or None
    member.manager = manager
    member.nuit = nuit or None

    member.id_type = id_type or None
    member.id_number = id_number or None
    member.id_issue_date = id_issue_date
    member.id_expiry_date = id_expiry_date
    member.kyc_notes = kyc_notes or None

    member.save(
        update_fields=[
            "first_name",
            "last_name",
            "legal_name",
            "is_company",
            "phone",
            "alt_phone",
            "email",
            "city",
            "address",
            "profession",
            "marital_status",
            "gender",
            "manager",
            "nuit",
            "id_type",
            "id_number",
            "id_issue_date",
            "id_expiry_date",
            "kyc_notes",
        ]
    )

    return JsonResponse({"success": True, "message": _("Membro actualizado com sucesso.")})




#============================================================================================================
#============================================================================================================
def deactivate_member(request, member_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": _("Método inválido.")}, status=405)

    try:
        member = Member.objects.get(pk=member_id, is_active=True)
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Membro não encontrado.")}, status=404)

    member.is_active = False
    member.save(update_fields=["is_active"])

    return JsonResponse({"success": True, "message": _("Membro desactivado com sucesso.")})




#============================================================================================================
#============================================================================================================
def member_detail_json(request, member_id):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": _("Não autenticado.")}, status=401)

    try:
        member = (
            Member.objects
            .select_related("manager")
            .get(pk=member_id, is_active=True)
        )
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Membro não encontrado.")}, status=404)

    loans = (
        Loan.objects
        .filter(member=member)
        .select_related("loan_type")
        .order_by("-created_at")
    )

    loans_data = [
        {
            "id": l.id,
            "principal_amount": str(l.principal_amount),
            "status": l.status,
            "loan_type": l.loan_type.name if l.loan_type else "",
            "created_at": l.created_at.strftime("%Y-%m-%d") if l.created_at else None,
            "release_date": l.release_date.strftime("%Y-%m-%d") if l.release_date else None,
        }
        for l in loans
    ]

    data = {
        "success": True,
        "member": {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "legal_name": member.legal_name,
            "is_company": member.is_company,
            "phone": member.phone,
            "alt_phone": member.alt_phone,
            "email": member.email,
            "city": member.city,
            "address": member.address,
            "profession": member.profession,
            "marital_status": member.marital_status,
            "gender": member.gender,
            "nuit": member.nuit,
            "id_type": member.id_type,
            "id_number": member.id_number,
            "id_issue_date": member.id_issue_date.strftime("%Y-%m-%d") if member.id_issue_date else None,
            "id_expiry_date": member.id_expiry_date.strftime("%Y-%m-%d") if member.id_expiry_date else None,
            "kyc_notes": member.kyc_notes,
            "manager_name": member.manager.get_full_name() or member.manager.username,
        },
        "loans": loans_data,
    }
    return JsonResponse(data)




#============================================================================================================
#============================================================================================================
