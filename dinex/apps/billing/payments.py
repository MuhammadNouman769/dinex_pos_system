"""
Paying for DineX without a card gateway (the way most Pakistani SaaS works):
the owner sends money by JazzCash / Easypaisa / bank, then tells DineX the transaction id.
XverLabs checks the money arrived and APPROVES, which marks the invoice paid and starts (or renews) the system.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.billing import services
from apps.billing.models import Invoice, PaymentAccount, PaymentSubmission, Plan, Subscription

MAX_PROOF_BYTES = 3 * 1024 * 1024
ALLOWED_PROOF = {"image/jpeg", "image/png", "image/webp"}


def account_dict(a):
    return {"id": a.id, "method": a.method, "method_label": a.get_method_display(), "account_title": a.account_title,
            "account_number": a.account_number, "bank_name": a.bank_name, "instructions": a.instructions,
            "is_active": a.is_active, "sort_order": a.sort_order}


def submission_dict(s, request=None, with_org=False):
    proof = None
    if s.proof:
        proof = request.build_absolute_uri(s.proof.url) if request is not None else s.proof.url
    d = {"id": s.id, "status": s.status, "status_label": s.get_status_display(), "amount": s.amount, "method": s.method,
         "reference": s.reference, "sender_name": s.sender_name, "sender_number": s.sender_number, "note": s.note,
         "proof": proof, "reject_reason": s.reject_reason, "created_at": s.created_at, "reviewed_at": s.reviewed_at,
         "invoice": s.invoice_id, "invoice_number": s.invoice.number if s.invoice else None,
         "invoice_amount": s.invoice.amount if s.invoice else None,
         "amount_matches": bool(s.invoice and s.invoice.amount == s.amount)}
    if with_org:
        d.update(organization=s.organization_id, organization_name=s.organization.name,
                 submitted_by=s.submitted_by.username if s.submitted_by else None)
    return d


def invoice_to_pay(sub):
    """The invoice a payment is for: the oldest unpaid one, or a fresh one for the next month."""
    due = sub.organization.invoices.filter(status=Invoice.Status.DUE).order_by("due_date", "id").first()
    if due is not None:
        return due
    today = timezone.localdate()
    start = sub.current_period_end if (sub.current_period_end and sub.current_period_end > today) else today
    return services.create_invoice(sub, start, services.add_months(start),
                                   note="Subscription payment" if sub.current_period_end else "First month")


def _clean_proof(proof):
    if proof is None:
        return None
    if proof.size > MAX_PROOF_BYTES:
        raise ValidationError({"proof": "The picture is too big (max 3 MB)."})
    if getattr(proof, "content_type", "") not in ALLOWED_PROOF:
        raise ValidationError({"proof": "Upload a JPG, PNG or WebP picture."})
    return proof


@transaction.atomic
def submit_payment(org, user, data, proof=None):
    sub = services.subscription_of(org)
    if sub is None:
        raise ValidationError({"detail": "This restaurant has no subscription."})
    if sub.status == Subscription.Status.ACTIVE and not org.invoices.filter(status=Invoice.Status.DUE).exists():
        raise ValidationError({"detail": "Your subscription is active and nothing is due right now."})
    if org.payment_submissions.filter(status=PaymentSubmission.Status.PENDING).exists():
        raise ValidationError({"detail": "You already sent a payment. We are checking it. You will be switched on as soon as it is confirmed."})

    errors = {}
    method = str(data.get("method") or "").strip()[:30]
    reference = str(data.get("reference") or "").strip()[:100]
    if not method:
        errors["method"] = "Choose how you paid."
    if len(reference) < 4:
        errors["reference"] = "Enter the transaction ID (TID) from your payment message."
    try:
        amount = Decimal(str(data.get("amount")))
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        amount = None
        errors["amount"] = "Enter the amount you sent."
    if errors:
        raise ValidationError(errors)
    if PaymentSubmission.objects.filter(reference__iexact=reference, status__in=["PENDING", "APPROVED"]).exists():
        raise ValidationError({"reference": "This transaction ID was already submitted."})

    invoice = invoice_to_pay(sub)
    sub_obj = PaymentSubmission.objects.create(
        organization=org, invoice=invoice, amount=amount, method=method, reference=reference,
        sender_name=str(data.get("sender_name") or "")[:120], sender_number=str(data.get("sender_number") or "")[:40],
        note=str(data.get("note") or "")[:255], proof=_clean_proof(proof), submitted_by=user)
    services.platform_audit(user, org, "payment_submitted", invoice=invoice.number, amount=amount, reference=reference)
    return sub_obj


@transaction.atomic
def approve_submission(submission, user):
    submission = PaymentSubmission.objects.select_for_update().select_related("invoice", "organization").get(pk=submission.pk)
    if submission.status != PaymentSubmission.Status.PENDING:
        raise ValidationError({"detail": f"This payment is already {submission.get_status_display().lower()}."})
    invoice = submission.invoice
    if invoice is None or invoice.status != Invoice.Status.DUE:
        raise ValidationError({"detail": "Its invoice is no longer due. Reject this payment or check the invoice."})
    services.mark_paid(invoice, user, method=submission.method, reference=submission.reference)
    submission.status = PaymentSubmission.Status.APPROVED
    submission.reviewed_by, submission.reviewed_at = user, timezone.now()
    submission.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    services.platform_audit(user, submission.organization, "payment_approved", reference=submission.reference, amount=submission.amount)
    return submission


@transaction.atomic
def reject_submission(submission, user, reason):
    submission = PaymentSubmission.objects.select_for_update().select_related("organization").get(pk=submission.pk)
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise ValidationError({"reason": "Tell the restaurant why (e.g. money not received)."})
    if submission.status != PaymentSubmission.Status.PENDING:
        raise ValidationError({"detail": f"This payment is already {submission.get_status_display().lower()}."})
    submission.status, submission.reject_reason = PaymentSubmission.Status.REJECTED, reason[:255]
    submission.reviewed_by, submission.reviewed_at = user, timezone.now()
    submission.save(update_fields=["status", "reject_reason", "reviewed_by", "reviewed_at"])
    services.platform_audit(user, submission.organization, "payment_rejected", reference=submission.reference, reason=reason)
    return submission


def choose_plan(org, user, plan_code):
    """Self-service plan choice while still on the free trial."""
    sub = services.subscription_of(org)
    if sub is None:
        raise ValidationError({"detail": "This restaurant has no subscription."})
    if sub.status != Subscription.Status.TRIAL:
        raise ValidationError({"detail": "To change your plan after paying, please contact XverLabs."})
    if org.invoices.filter(status=Invoice.Status.DUE).exists() or org.payment_submissions.filter(status="PENDING").exists():
        raise ValidationError({"detail": "You have a payment in progress. Contact XverLabs to change plan."})
    if not Plan.objects.filter(code=plan_code, is_active=True).exists():
        raise ValidationError({"plan": "Unknown plan."})
    services.apply_action(sub, user, "change_plan", {"plan": plan_code})
    return sub
