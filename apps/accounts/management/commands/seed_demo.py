"""Management command to populate sample seed data.

Idempotent: running it twice creates 0 new objects on subsequent runs.
"""

from datetime import timedelta
from decimal import Decimal
import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.deposits.models import Deposit
from apps.institutions.models import Institution


class Command(BaseCommand):
    help = "Seed database with sample institutions, users, and deposits."

    def handle(self, *args, **options):
        counts = {
            "institutions_created": 0,
            "institutions_updated": 0,
            "users_created": 0,
            "deposits_created": 0,
        }

        # ------------------------------------------------------------------
        # 1. Institutions (update_or_create by code)
        # ------------------------------------------------------------------
        institutions_data = [
            {
                "code": "CIT-CHD",
                "name": "Chandigarh Institute of Technology",
                "contact_email": "admin@cit-chd.example.com",
            },
            {
                "code": "REC-JPR",
                "name": "Rajasthan Engineering College",
                "contact_email": "admin@rec-jpr.example.com",
            },
        ]

        institutions_map = {}
        for inst_data in institutions_data:
            code = inst_data["code"]
            inst, created = Institution.objects.update_or_create(
                code=code,
                defaults={
                    "name": inst_data["name"],
                    "contact_email": inst_data["contact_email"],
                },
            )
            institutions_map[code] = inst
            if created:
                counts["institutions_created"] += 1
            else:
                counts["institutions_updated"] += 1

        inst_cit = institutions_map["CIT-CHD"]
        inst_rec = institutions_map["REC-JPR"]

        # ------------------------------------------------------------------
        # 2. Users (set password only when user is created)
        # ------------------------------------------------------------------
        default_password = os.environ.get("DEMO_PASSWORD", "Demo@12345")

        users_spec = [
            {
                "username": "admin_aicte",
                "role": User.Roles.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "institution": None,
                "email": "admin_aicte@example.com",
            },
            {
                "username": "officer_region1",
                "role": User.Roles.OFFICER,
                "is_staff": False,
                "is_superuser": False,
                "institution": None,
                "email": "officer_region1@example.com",
            },
            {
                "username": "cit_user",
                "role": User.Roles.INSTITUTION,
                "is_staff": False,
                "is_superuser": False,
                "institution": inst_cit,
                "email": "cit_user@example.com",
            },
            {
                "username": "rec_user",
                "role": User.Roles.INSTITUTION,
                "is_staff": False,
                "is_superuser": False,
                "institution": inst_rec,
                "email": "rec_user@example.com",
            },
        ]

        users_map = {}
        for u_info in users_spec:
            username = u_info["username"]
            user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.create(
                    username=username,
                    role=u_info["role"],
                    is_staff=u_info["is_staff"],
                    is_superuser=u_info["is_superuser"],
                    institution=u_info["institution"],
                    email=u_info["email"],
                )
                user.set_password(default_password)
                user.save()
                counts["users_created"] += 1
            users_map[username] = user

        # ------------------------------------------------------------------
        # 3. Deposits
        # ------------------------------------------------------------------
        today = timezone.localdate()
        bank_name = "State Bank of India"

        # RENEWED deposit for CIT-CHD (previous deposit for CIT-CHD-ACTIVE)
        renewed_deposit, renewed_created = Deposit.objects.get_or_create(
            bank_name=bank_name,
            reference_number="CIT-CHD-RENEWED",
            defaults={
                "institution": inst_cit,
                "instrument_type": Deposit.InstrumentType.FDR,
                "bank_branch": "Main Branch",
                "amount": Decimal("500000.00"),
                "issue_date": today - timedelta(days=425),
                "maturity_date": today - timedelta(days=60),
                # Set status directly with the model. This is seed data, so bypassing transitions is intentional.
                "status": Deposit.Status.RENEWED,
                "verification_source": Deposit.VerificationSource.INSTITUTION_SUBMITTED,
                "previous_deposit": None,
                "created_by": users_map["cit_user"],
            },
        )
        if renewed_created:
            counts["deposits_created"] += 1

        cit_deposits = [
            {
                "reference_number": "CIT-CHD-SUBMITTED",
                "status": Deposit.Status.SUBMITTED,
                "issue_date": today - timedelta(days=15),
                "maturity_date": today + timedelta(days=350),
                "previous_deposit": None,
            },
            {
                "reference_number": "CIT-CHD-UNDER_SCRUTINY",
                "status": Deposit.Status.UNDER_SCRUTINY,
                "issue_date": today - timedelta(days=20),
                "maturity_date": today + timedelta(days=345),
                "previous_deposit": None,
            },
            {
                "reference_number": "CIT-CHD-VERIFIED",
                "status": Deposit.Status.VERIFIED,
                "issue_date": today - timedelta(days=25),
                "maturity_date": today + timedelta(days=340),
                "previous_deposit": None,
            },
            {
                "reference_number": "CIT-CHD-DISCREPANCY",
                "status": Deposit.Status.DISCREPANCY,
                "issue_date": today - timedelta(days=30),
                "maturity_date": today + timedelta(days=335),
                "previous_deposit": None,
            },
            {
                "reference_number": "CIT-CHD-ACTIVE",
                "status": Deposit.Status.ACTIVE,
                "issue_date": today - timedelta(days=60),
                "maturity_date": today + timedelta(days=305),
                "previous_deposit": renewed_deposit,  # ACTIVE child linked through previous_deposit
            },
            {
                "reference_number": "CIT-CHD-EXPIRING",
                "status": Deposit.Status.EXPIRING,
                "issue_date": today - timedelta(days=355),
                "maturity_date": today + timedelta(days=10),  # maturity 10 days from today
                "previous_deposit": None,
            },
            {
                "reference_number": "CIT-CHD-MATURED",
                "status": Deposit.Status.MATURED,
                "issue_date": today - timedelta(days=395),
                "maturity_date": today - timedelta(days=30),  # maturity 30 days ago
                "previous_deposit": None,
            },
        ]

        for dep_spec in cit_deposits:
            _, created = Deposit.objects.get_or_create(
                bank_name=bank_name,
                reference_number=dep_spec["reference_number"],
                defaults={
                    "institution": inst_cit,
                    "instrument_type": Deposit.InstrumentType.FDR,
                    "bank_branch": "Main Branch",
                    "amount": Decimal("500000.00"),
                    "issue_date": dep_spec["issue_date"],
                    "maturity_date": dep_spec["maturity_date"],
                    # Set status directly with the model. This is seed data, so bypassing transitions is intentional.
                    "status": dep_spec["status"],
                    "verification_source": Deposit.VerificationSource.INSTITUTION_SUBMITTED,
                    "previous_deposit": dep_spec["previous_deposit"],
                    "created_by": users_map["cit_user"],
                },
            )
            if created:
                counts["deposits_created"] += 1

        # One ACTIVE deposit for REC-JPR, so scoping can be seen
        _, created_b = Deposit.objects.get_or_create(
            bank_name=bank_name,
            reference_number="REC-JPR-ACTIVE",
            defaults={
                "institution": inst_rec,
                "instrument_type": Deposit.InstrumentType.FDR,
                "bank_branch": "Main Branch",
                "amount": Decimal("750000.00"),
                "issue_date": today - timedelta(days=30),
                "maturity_date": today + timedelta(days=335),
                # Set status directly with the model. This is seed data, so bypassing transitions is intentional.
                "status": Deposit.Status.ACTIVE,
                "verification_source": Deposit.VerificationSource.INSTITUTION_SUBMITTED,
                "previous_deposit": None,
                "created_by": users_map["rec_user"],
            },
        )
        if created_b:
            counts["deposits_created"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed completed: {counts['institutions_created']} new institution(s), "
                f"{counts['users_created']} new user(s), "
                f"{counts['deposits_created']} new deposit(s)."
            )
        )

        # ------------------------------------------------------------------
        # 4. Print credentials table
        # ------------------------------------------------------------------
        self.stdout.write("\nLogin Credentials:")
        header = f"{'Username':<15} {'Role':<15} {'Institution':<35} {'Password':<15}"
        sep = "-" * len(header)
        self.stdout.write(sep)
        self.stdout.write(header)
        self.stdout.write(sep)
        table_rows = [
            ("admin_aicte", "ADMIN", "-", default_password),
            ("officer_region1", "OFFICER", "-", default_password),
            ("cit_user", "INSTITUTION", "Chandigarh Institute of Technology", default_password),
            ("rec_user", "INSTITUTION", "Rajasthan Engineering College", default_password),
        ]
        for uname, urole, uinst, upass in table_rows:
            self.stdout.write(f"{uname:<15} {urole:<15} {uinst:<35} {upass:<15}")
        self.stdout.write(sep)
