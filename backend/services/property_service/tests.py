"""
Unit & API Tests for Service 2 (Property & Room) have been consolidated into:
    `backend/services/property_service/testing/`
- `testing/unit_tests/`:
    - `test_models.py` (S2-MOD-001..046)
    - `test_serializers.py` (S2-SER-001..044)
    - `test_services.py` (S2-BIZ-001..028)
    - `test_views.py` (S2-API-001..063)
    - `test_search_filter.py` (S2-FLT-001..042)
    - `test_permissions.py` (S2-SEC-001..034, including migrated S2-LEG-029 & S2-LEG-033)
- `testing/api_tests/`:
    - `test_maintenance_api.py` (S2-MAPI-001..004, migrated from S2-LEG-018..021)

Django's `DiscoverRunner` (`python manage.py test services.property_service`) automatically
discovers all 261 tests across `testing/unit_tests/` and `testing/api_tests/`.
See `testing/reports/LEGACY_TEST_MIGRATION.md` for the full 35-test migration & deduplication matrix.
"""
