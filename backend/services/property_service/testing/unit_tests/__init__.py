"""
Bộ Unit/API test Sprint 1 cho SERVICE 2 — Property & Room (:8002).

Đặt trong package `unit_tests` (không phải `tests/`) vì app đã có sẵn `tests.py`;
một package `tests/` sẽ che khuất file đó. Các test cũ trong `tests.py` được giữ nguyên.

Chạy (từ thư mục backend, dùng SQLite tạm — không đụng database phát triển):
    $env:DB_ENGINE='sqlite'; $env:DJANGO_SETTINGS_MODULE='config.service_settings.property'
    python manage.py test services.property_service.unit_tests -v 2
"""
