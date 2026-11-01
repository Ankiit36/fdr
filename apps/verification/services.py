"""Bank verification services for deposit verification."""

from abc import ABC, abstractmethod

from django.utils import timezone

from apps.audit.services import write_audit_log
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError, change_status


class BankVerificationService(ABC):
    """Abstract port for bank verification."""

    @abstractmethod
    def verify(self, deposit: Deposit) -> bool:
        """Run the bank verification and return True when the bank confirms."""
        raise NotImplementedError


class MockBankVerificationService(BankVerificationService):
    """Mock bank verification used in development and tests."""

    def __init__(self, confirmed: bool = True):
        self.confirmed = confirmed

    def verify(self, deposit: Deposit) -> bool:
        return self.confirmed


def verify_deposit(deposit, officer, bank_verification_service=None, note=None, outcome=None):
    """Run officer verification through the bank verification service.

    - If the bank confirms: verification_source is set to BANK_CONFIRMED and
      the deposit status becomes VERIFIED.
    - If the bank does not confirm: verification_source stays
      INSTITUTION_SUBMITTED and a manual VERIFIED or DISCREPANCY outcome
      requires an officer note.
    """
    if bank_verification_service is None:
        bank_verification_service = MockBankVerificationService()

    confirmed = bank_verification_service.verify(deposit)

    if confirmed:
        deposit.verification_source = Deposit.VerificationSource.BANK_CONFIRMED
        deposit.verification_tier = Deposit.VerificationTier.BANK_CONFIRMED
        change_status(
            deposit,
            Deposit.Status.VERIFIED,
            officer,
            note=note,
            audit_action="VERIFICATION_CONFIRMED",
        )
        deposit.save(update_fields=["verification_source", "verification_tier", "updated_at"])
        return Deposit.Status.VERIFIED

    # Bank did not confirm: institution submitted evidence remains authoritative.
    if outcome in (Deposit.Status.VERIFIED, Deposit.Status.DISCREPANCY) and not note:
        raise DomainError(
            "A note is required when recording a manual VERIFIED or DISCREPANCY outcome "
            f"without bank confirmation for deposit '{deposit.reference_number}'."
        )

    if outcome is None:
        # Bank did not confirm; keep the institution submitted state.
        return deposit.status

    return change_status(deposit, outcome, officer, note=note)


def apply_officer_status(deposit, officer, new_status, note=None, bank_verification_service=None):
    """Apply an officer status decision (UNDER_SCRUTINY, VERIFIED or DISCREPANCY)."""
    if new_status == Deposit.Status.UNDER_SCRUTINY:
        return change_status(deposit, Deposit.Status.UNDER_SCRUTINY, officer, note=note)

    return verify_deposit(
        deposit,
        officer,
        bank_verification_service=bank_verification_service,
        note=note,
        outcome=new_status,
    )
