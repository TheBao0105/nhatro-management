"""
SOA Database Router
Định tuyến database riêng cho từng microservice theo kiến trúc SOA.
Mỗi service sở hữu cơ sở dữ liệu riêng, hoàn toàn độc lập, không có foreign key chéo service.
"""

class ServiceDatabaseRouter:
    """
    Router phân tách cơ sở dữ liệu cho từng service trong hệ thống Quản lý Nhà trọ:
    - identity_service -> default (nhatro_identity_db)
    - property_service -> property_db (nhatro_property_db)
    - tenant_service   -> tenant_db (nhatro_tenant_db)
    - contract_service -> contract_db (nhatro_contract_db)
    - billing_notification_service -> billing_db (nhatro_billing_db)
    """

    APP_TO_DB = {
        'identity_service': 'default',
        'property_service': 'property_db',
        'tenant_service': 'tenant_db',
        'contract_service': 'contract_db',
        'billing_notification_service': 'billing_db',
    }

    def db_for_read(self, model, **hints):
        app_label = model._meta.app_label
        return self.APP_TO_DB.get(app_label, 'default')

    def db_for_write(self, model, **hints):
        app_label = model._meta.app_label
        return self.APP_TO_DB.get(app_label, 'default')

    def allow_relation(self, obj1, obj2, **hints):
        """
        Trong kiến trúc SOA, KHÔNG cho phép quan hệ khóa ngoại (ForeignKey)
        giữa các service khác nhau. Chỉ cho phép quan hệ nội bộ trong cùng 1 service.
        """
        # Cho phép nếu cùng app
        if obj1._meta.app_label == obj2._meta.app_label:
            return True
        # Django internal apps
        if obj1._meta.app_label in ('auth', 'contenttypes', 'sessions', 'admin') and \
           obj2._meta.app_label in ('auth', 'contenttypes', 'sessions', 'admin', 'identity_service'):
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Đảm bảo migrations của từng service chỉ chạy trên đúng database của service đó.
        """
        target_db = self.APP_TO_DB.get(app_label)
        if target_db:
            return db == target_db
        # Django built-in apps (admin, auth, contenttypes, sessions) chạy trên 'default' (Identity)
        return db == 'default'

