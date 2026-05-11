"""Unit and property-based tests for DatabaseWriter."""

import os
import tempfile

import pytest

from src.database import DatabaseWriter
from src.extractor import AccountInfo


# --- Fixtures ---


@pytest.fixture
def db_writer():
    """Create a DatabaseWriter with a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    writer = DatabaseWriter(db_path=path)
    yield writer
    writer.close()
    os.unlink(path)


@pytest.fixture
def db_path():
    """Provide a temporary database path and clean up after test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


# --- Unit Tests: Schema Creation ---


class TestSchemaCreation:
    """Tests for database schema creation."""

    def test_accounts_table_exists(self, db_writer):
        """The accounts table is created on initialization."""
        cursor = db_writer.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
        )
        assert cursor.fetchone() is not None

    def test_credits_history_table_exists(self, db_writer):
        """The credits_history table is created on initialization."""
        cursor = db_writer.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='credits_history'"
        )
        assert cursor.fetchone() is not None

    def test_accounts_table_columns(self, db_writer):
        """The accounts table has the expected columns."""
        cursor = db_writer.conn.cursor()
        cursor.execute("PRAGMA table_info(accounts)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "profile_name", "email", "user_id", "credits_used",
            "credits_total", "plan_name", "reset_date", "extracted_at",
        }
        assert columns == expected

    def test_credits_history_table_columns(self, db_writer):
        """The credits_history table has the expected columns."""
        cursor = db_writer.conn.cursor()
        cursor.execute("PRAGMA table_info(credits_history)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "id", "profile_name", "credits_used",
            "credits_total", "plan_name", "extracted_at",
        }
        assert columns == expected

    def test_tables_created_if_not_exist(self, db_path):
        """Tables are created even if the database file is new."""
        writer = DatabaseWriter(db_path=db_path)
        cursor = writer.conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        count = cursor.fetchone()[0]
        writer.close()
        assert count >= 3

    def test_scrape_errors_table_exists(self, db_writer):
        """The scrape_errors table is created on initialization."""
        cursor = db_writer.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scrape_errors'"
        )
        assert cursor.fetchone() is not None

    def test_scrape_errors_table_columns(self, db_writer):
        """The scrape_errors table has the expected columns."""
        cursor = db_writer.conn.cursor()
        cursor.execute("PRAGMA table_info(scrape_errors)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {"id", "profile_name", "error_message", "attempts", "failed_at"}
        assert columns == expected


# --- Unit Tests: save_account ---


class TestSaveAccount:
    """Tests for save_account() method."""

    def test_insert_new_account(self, db_writer):
        """A new account is inserted into the accounts table."""
        info = AccountInfo(
            email="test@example.com",
            user_id="usr-123",
            credits_used=500.0,
            credits_total=2000.0,
            plan_name="Pro",
            reset_date="2024-02-01",
        )
        db_writer.save_account("Profile 1", info)

        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE profile_name = ?", ("Profile 1",))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Profile 1"
        assert row[1] == "test@example.com"
        assert row[2] == "usr-123"
        assert row[3] == 500.0
        assert row[4] == 2000.0
        assert row[5] == "Pro"
        assert row[6] == "2024-02-01"
        assert row[7] is not None  # extracted_at

    def test_insert_creates_history_record(self, db_writer):
        """Saving an account also creates a credits_history record."""
        info = AccountInfo(credits_used=100.0, credits_total=1000.0, plan_name="Free")
        db_writer.save_account("Profile 1", info)

        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT * FROM credits_history WHERE profile_name = ?", ("Profile 1",))
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][2] == 100.0  # credits_used
        assert rows[0][3] == 1000.0  # credits_total
        assert rows[0][4] == "Free"  # plan_name

    def test_upsert_updates_existing_account(self, db_writer):
        """Saving the same profile again updates the accounts record."""
        info1 = AccountInfo(email="old@example.com", credits_used=100.0, credits_total=1000.0)
        info2 = AccountInfo(email="new@example.com", credits_used=200.0, credits_total=1000.0)

        db_writer.save_account("Profile 1", info1)
        db_writer.save_account("Profile 1", info2)

        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT email, credits_used FROM accounts WHERE profile_name = ?", ("Profile 1",))
        row = cursor.fetchone()
        assert row[0] == "new@example.com"
        assert row[1] == 200.0

    def test_upsert_keeps_single_account_record(self, db_writer):
        """Multiple saves for same profile result in exactly one accounts record."""
        info = AccountInfo(credits_used=100.0, credits_total=1000.0)

        db_writer.save_account("Profile 1", info)
        db_writer.save_account("Profile 1", info)
        db_writer.save_account("Profile 1", info)

        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT count(*) FROM accounts WHERE profile_name = ?", ("Profile 1",))
        count = cursor.fetchone()[0]
        assert count == 1

    def test_multiple_saves_create_multiple_history_records(self, db_writer):
        """Each save creates a new credits_history record."""
        info = AccountInfo(credits_used=100.0, credits_total=1000.0)

        db_writer.save_account("Profile 1", info)
        db_writer.save_account("Profile 1", info)
        db_writer.save_account("Profile 1", info)

        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT count(*) FROM credits_history WHERE profile_name = ?", ("Profile 1",))
        count = cursor.fetchone()[0]
        assert count == 3

    def test_save_with_none_fields(self, db_writer):
        """Saving an account with None fields stores NULL in the database."""
        info = AccountInfo()  # All fields None
        db_writer.save_account("Profile 1", info)

        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT email, user_id, credits_used FROM accounts WHERE profile_name = ?", ("Profile 1",))
        row = cursor.fetchone()
        assert row[0] is None
        assert row[1] is None
        assert row[2] is None


# --- Unit Tests: get_history ---


class TestGetHistory:
    """Tests for get_history() method."""

    def test_returns_empty_list_for_unknown_profile(self, db_writer):
        """Returns empty list when no history exists for the profile."""
        history = db_writer.get_history("nonexistent")
        assert history == []

    def test_returns_history_records(self, db_writer):
        """Returns all history records for a profile."""
        info1 = AccountInfo(credits_used=100.0, credits_total=1000.0, plan_name="Free")
        info2 = AccountInfo(credits_used=200.0, credits_total=1000.0, plan_name="Pro")

        db_writer.save_account("Profile 1", info1)
        db_writer.save_account("Profile 1", info2)

        history = db_writer.get_history("Profile 1")
        assert len(history) == 2
        assert history[0]["credits_used"] == 100.0
        assert history[1]["credits_used"] == 200.0

    def test_history_ordered_by_timestamp(self, db_writer):
        """History records are ordered by extracted_at ascending."""
        import time

        info1 = AccountInfo(credits_used=100.0, credits_total=1000.0)
        info2 = AccountInfo(credits_used=200.0, credits_total=1000.0)

        db_writer.save_account("Profile 1", info1)
        time.sleep(0.01)  # Ensure different timestamps
        db_writer.save_account("Profile 1", info2)

        history = db_writer.get_history("Profile 1")
        assert history[0]["extracted_at"] <= history[1]["extracted_at"]

    def test_history_contains_expected_keys(self, db_writer):
        """Each history record contains the expected dictionary keys."""
        info = AccountInfo(credits_used=100.0, credits_total=1000.0, plan_name="Pro")
        db_writer.save_account("Profile 1", info)

        history = db_writer.get_history("Profile 1")
        assert len(history) == 1
        record = history[0]
        assert "id" in record
        assert "profile_name" in record
        assert "credits_used" in record
        assert "credits_total" in record
        assert "plan_name" in record
        assert "extracted_at" in record

    def test_history_only_returns_specified_profile(self, db_writer):
        """get_history only returns records for the specified profile."""
        info = AccountInfo(credits_used=100.0, credits_total=1000.0)

        db_writer.save_account("Profile 1", info)
        db_writer.save_account("Profile 2", info)

        history = db_writer.get_history("Profile 1")
        assert len(history) == 1
        assert history[0]["profile_name"] == "Profile 1"


# --- Unit Tests: save_error ---


class TestSaveError:
    """Tests for save_error() method."""

    def test_save_error_inserts_record(self, db_writer):
        """save_error inserts a record into scrape_errors table."""
        db_writer.save_error("Profile_1", "Connection timeout", 5)
        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT profile_name, error_message, attempts FROM scrape_errors")
        row = cursor.fetchone()
        assert row == ("Profile_1", "Connection timeout", 5)

    def test_save_error_multiple_records(self, db_writer):
        """Multiple errors for same profile create multiple records."""
        db_writer.save_error("Profile_1", "Error 1", 5)
        db_writer.save_error("Profile_1", "Error 2", 5)
        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT count(*) FROM scrape_errors WHERE profile_name = ?", ("Profile_1",))
        assert cursor.fetchone()[0] == 2

    def test_save_error_stores_failed_at(self, db_writer):
        """save_error stores a non-null failed_at timestamp."""
        db_writer.save_error("Profile_1", "err", 3)
        cursor = db_writer.conn.cursor()
        cursor.execute("SELECT failed_at FROM scrape_errors")
        assert cursor.fetchone()[0] is not None


# --- Unit Tests: close ---


class TestClose:
    """Tests for close() method."""

    def test_close_closes_connection(self, db_path):
        """Closing the writer closes the database connection."""
        writer = DatabaseWriter(db_path=db_path)
        writer.close()

        # Attempting to use the connection after close should raise
        with pytest.raises(Exception):
            writer.conn.execute("SELECT 1")


# --- Property-Based Tests ---

from hypothesis import given, settings, assume
from hypothesis import strategies as st


def account_info_strategy():
    """Strategy for generating arbitrary AccountInfo instances."""
    return st.builds(
        AccountInfo,
        email=st.one_of(st.none(), st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")),
        user_id=st.one_of(st.none(), st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")),
        credits_used=st.one_of(st.none(), st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False)),
        credits_total=st.one_of(st.none(), st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False)),
        plan_name=st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != "")),
        reset_date=st.one_of(st.none(), st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != "")),
    )


@given(
    infos=st.lists(account_info_strategy(), min_size=1, max_size=10),
)
@settings(max_examples=200)
def test_property_database_upsert_round_trip(infos):
    """
    Feature: kiro-account-scraper, Property 6: Database upsert round-trip

    **Validates: Requirements 5.2, 5.4**

    For any sequence of AccountInfo records saved under the same profile name,
    reading back from the database SHALL always return the most recently saved
    record with all fields matching, and exactly one record SHALL exist for that
    profile in accounts table. credits_history should contain ALL records in
    chronological order.
    """
    # Use in-memory database for speed
    writer = DatabaseWriter(db_path=":memory:")
    profile_name = "test-profile"

    # Save all records sequentially
    for info in infos:
        writer.save_account(profile_name, info)

    # Verify: exactly one record in accounts table
    cursor = writer.conn.cursor()
    cursor.execute("SELECT count(*) FROM accounts WHERE profile_name = ?", (profile_name,))
    count = cursor.fetchone()[0]
    assert count == 1, f"Expected 1 account record, got {count}"

    # Verify: the accounts record matches the LAST saved info
    cursor.execute(
        "SELECT email, user_id, credits_used, credits_total, plan_name, reset_date FROM accounts WHERE profile_name = ?",
        (profile_name,),
    )
    row = cursor.fetchone()
    last_info = infos[-1]
    assert row[0] == last_info.email
    assert row[1] == last_info.user_id
    if last_info.credits_used is not None:
        assert abs(row[2] - last_info.credits_used) < 1e-6
    else:
        assert row[2] is None
    if last_info.credits_total is not None:
        assert abs(row[3] - last_info.credits_total) < 1e-6
    else:
        assert row[3] is None
    assert row[4] == last_info.plan_name
    assert row[5] == last_info.reset_date

    # Verify: credits_history contains ALL records in order
    history = writer.get_history(profile_name)
    assert len(history) == len(infos), f"Expected {len(infos)} history records, got {len(history)}"

    # Verify chronological order
    for i in range(1, len(history)):
        assert history[i]["extracted_at"] >= history[i - 1]["extracted_at"]

    # Verify each history record matches the corresponding saved info
    for i, (record, info) in enumerate(zip(history, infos)):
        if info.credits_used is not None:
            assert abs(record["credits_used"] - info.credits_used) < 1e-6
        else:
            assert record["credits_used"] is None
        if info.credits_total is not None:
            assert abs(record["credits_total"] - info.credits_total) < 1e-6
        else:
            assert record["credits_total"] is None
        assert record["plan_name"] == info.plan_name

    writer.close()
