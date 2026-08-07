"""ORM metadata, relationships, and enum value tests for Technician tables."""

import src.database.models  # noqa: F401
from src.database.base import Base
from src.database.models.technician_profile import TechnicianProfile
from src.database.models.technician_skill import TechnicianSkill
from src.database.models.ticket_assignment import TicketAssignment
from src.models.enums import AssignmentStatus


class TestTechnicianTablesRegistered:
    def test_technician_profiles_in_metadata(self):
        assert "technician_profiles" in Base.metadata.tables

    def test_technician_skills_in_metadata(self):
        assert "technician_skills" in Base.metadata.tables

    def test_ticket_assignments_in_metadata(self):
        assert "ticket_assignments" in Base.metadata.tables

    def test_no_public_users_table(self):
        assert "users" not in Base.metadata.tables

    def test_no_role_enum_in_any_column(self):
        from sqlalchemy import Enum as SQLEnum

        enum_names = {
            col.type.name
            for table in Base.metadata.tables.values()
            for col in table.c
            if isinstance(col.type, SQLEnum)
        }
        assert "role_enum" not in enum_names

    def test_assignment_status_enum_present(self):
        from sqlalchemy import Enum as SQLEnum

        enum_names = {
            col.type.name
            for table in Base.metadata.tables.values()
            for col in table.c
            if isinstance(col.type, SQLEnum)
        }
        assert "assignment_status_enum" in enum_names


class TestTechnicianProfileMetadata:
    def test_primary_key_is_id(self):
        table = Base.metadata.tables["technician_profiles"]
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["id"]

    def test_email_column_nullable_false(self):
        col = Base.metadata.tables["technician_profiles"].c.email
        assert col.nullable is False

    def test_email_has_no_column_level_unique(self):
        # Uniqueness must be enforced via the index only (consistent with bql_staff).
        col = Base.metadata.tables["technician_profiles"].c.email
        assert not col.unique

    def test_email_unique_index_exists(self):
        table = Base.metadata.tables["technician_profiles"]
        index_names = {idx.name for idx in table.indexes}
        assert "ix_technician_profiles_email" in index_names

    def test_is_active_and_is_available_have_server_defaults(self):
        table = Base.metadata.tables["technician_profiles"]
        assert table.c.is_active.server_default is not None
        assert table.c.is_available.server_default is not None

    def test_phone_number_column_nullable(self):
        col = Base.metadata.tables["technician_profiles"].c.phone_number
        assert col.nullable is True


class TestTechnicianSkillMetadata:
    def test_unique_constraint_on_technician_category(self):
        from sqlalchemy import UniqueConstraint

        table = Base.metadata.tables["technician_skills"]
        uq_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
        assert "uq_technician_skills_technician_category" in uq_names

    def test_fk_to_technician_profiles(self):
        fks = Base.metadata.tables["technician_skills"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "technician_profiles.id" in targets


class TestTicketAssignmentMetadata:
    def test_fk_to_tickets(self):
        fks = Base.metadata.tables["ticket_assignments"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "tickets.id" in targets

    def test_fk_to_technician_profiles(self):
        fks = Base.metadata.tables["ticket_assignments"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "technician_profiles.id" in targets

    def test_work_note_and_unable_reason_columns_exist(self):
        table = Base.metadata.tables["ticket_assignments"]
        assert table.c.work_note.type.length == 1000
        assert table.c.unable_reason.type.length == 500

    def test_one_active_partial_unique_index_exists(self):
        table = Base.metadata.tables["ticket_assignments"]
        index_names = {idx.name for idx in table.indexes}
        assert "uq_ticket_assignments_one_active_per_ticket" in index_names


class TestAssignmentStatusValues:
    def test_all_values_present(self):
        values = {member.value for member in AssignmentStatus}
        assert values == {"assigned", "accepted", "in_progress", "completed", "unable_to_handle"}

    def test_assigned_is_default(self):
        assert AssignmentStatus.ASSIGNED.value == "assigned"

    def test_completed_exists_for_future_contract(self):
        assert AssignmentStatus.COMPLETED in AssignmentStatus


class TestTechnicianOrmRelationships:
    def test_technician_profile_has_skills_relationship(self):
        assert hasattr(TechnicianProfile, "skills")

    def test_technician_profile_has_assignments_relationship(self):
        assert hasattr(TechnicianProfile, "assignments")

    def test_technician_skill_has_technician_relationship(self):
        assert hasattr(TechnicianSkill, "technician")

    def test_ticket_assignment_has_ticket_relationship(self):
        assert hasattr(TicketAssignment, "ticket")

    def test_ticket_assignment_has_technician_relationship(self):
        assert hasattr(TicketAssignment, "technician")
