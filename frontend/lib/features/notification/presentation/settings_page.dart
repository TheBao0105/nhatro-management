import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_table.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/page_header.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../providers/auth_provider.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _elecCtrl = TextEditingController(text: '3500');
  final _waterCtrl = TextEditingController(text: '18000');
  final _netCtrl = TextEditingController(text: '100000');

  void _openChangePasswordDialog() {
    final formKey = GlobalKey<FormState>();
    final oldCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Đổi mật khẩu tài khoản', style: AppTypography.sectionTitle),
        content: SizedBox(
          width: 420,
          child: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AppTextField(
                  label: 'Mật khẩu hiện tại',
                  controller: oldCtrl,
                  requiredField: true,
                  obscureText: true,
                ),
                const SizedBox(height: 12),
                AppTextField(
                  label: 'Mật khẩu mới',
                  controller: newCtrl,
                  requiredField: true,
                  obscureText: true,
                  validator: (v) {
                    if (v == null || v.trim().length < 6) {
                      return 'Mật khẩu mới cần tối thiểu 6 ký tự';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                AppTextField(
                  label: 'Xác nhận mật khẩu mới',
                  controller: confirmCtrl,
                  requiredField: true,
                  obscureText: true,
                  validator: (v) {
                    if (v != newCtrl.text) return 'Mật khẩu xác nhận không khớp';
                    return null;
                  },
                ),
              ],
            ),
          ),
        ),
        actions: [
          AppButton(
            label: 'Hủy',
            variant: AppButtonVariant.outlined,
            onPressed: () => Navigator.pop(ctx),
          ),
          AppButton(
            label: 'Đổi mật khẩu',
            onPressed: () async {
              if (!(formKey.currentState?.validate() ?? false)) return;
              final err = await context
                  .read<AuthProvider>()
                  .changePassword(oldCtrl.text, newCtrl.text);
              if (!ctx.mounted || !mounted) return;
              if (err != null) {
                showErrorToast(context, err);
                return;
              }
              Navigator.pop(ctx);
              showSuccessToast(context, 'Đổi mật khẩu thành công.');
            },
          ),
        ],
      ),
    );
  }

  void _openProfileDialog(AuthProvider auth) {
    final user = auth.user ?? const <String, dynamic>{};
    final formKey = GlobalKey<FormState>();
    final firstCtrl = TextEditingController(text: '${user['first_name'] ?? ''}');
    final lastCtrl = TextEditingController(text: '${user['last_name'] ?? ''}');
    final emailCtrl = TextEditingController(text: '${user['email'] ?? ''}');
    final phoneCtrl = TextEditingController(text: '${user['phone_number'] ?? ''}');
    final addressCtrl = TextEditingController(text: '${user['address'] ?? ''}');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cập nhật hồ sơ cá nhân', style: AppTypography.sectionTitle),
        content: SizedBox(
          width: 480,
          child: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(child: AppTextField(label: 'Họ', controller: lastCtrl)),
                      const SizedBox(width: 12),
                      Expanded(child: AppTextField(label: 'Tên', controller: firstCtrl)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  AppTextField(label: 'Email', controller: emailCtrl),
                  const SizedBox(height: 12),
                  AppTextField(label: 'Số điện thoại', controller: phoneCtrl),
                  const SizedBox(height: 12),
                  AppTextField(label: 'Địa chỉ', controller: addressCtrl),
                ],
              ),
            ),
          ),
        ),
        actions: [
          AppButton(
            label: 'Hủy',
            variant: AppButtonVariant.outlined,
            onPressed: () => Navigator.pop(ctx),
          ),
          AppButton(
            label: 'Lưu hồ sơ',
            onPressed: () async {
              if (!(formKey.currentState?.validate() ?? false)) return;
              final err = await auth.updateProfile({
                'first_name': firstCtrl.text.trim(),
                'last_name': lastCtrl.text.trim(),
                'email': emailCtrl.text.trim(),
                'phone_number': phoneCtrl.text.trim(),
                'address': addressCtrl.text.trim(),
              });
              if (!ctx.mounted || !mounted) return;
              if (err != null) {
                showErrorToast(context, err);
                return;
              }
              Navigator.pop(ctx);
              showSuccessToast(context, 'Đã cập nhật thông tin tài khoản.');
            },
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _elecCtrl.dispose();
    _waterCtrl.dispose();
    _netCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user ?? const <String, dynamic>{};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          title: 'Cài đặt',
          subtitle: 'Thông tin tài khoản đăng nhập, mật khẩu và cấu hình cá nhân.',
          actions: [
            AppButton(
              label: 'Đổi mật khẩu',
              icon: Icons.lock_reset_rounded,
              variant: AppButtonVariant.outlined,
              onPressed: _openChangePasswordDialog,
            ),
          ],
        ),

        // Current User Profile Card (Service 1: Identity)
        AppSurfaceCard(
          child: LayoutBuilder(builder: (context, constraints) {
            final narrow = constraints.maxWidth < 560;
            final actions = Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                AppButton(
                  label: 'Sửa hồ sơ',
                  compact: true,
                  variant: AppButtonVariant.outlined,
                  onPressed: () => _openProfileDialog(auth),
                ),
                AppButton(
                  label: 'Đăng xuất',
                  compact: true,
                  variant: AppButtonVariant.danger,
                  onPressed: () => auth.logout(),
                ),
              ],
            );
            final info = Row(
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: AppColors.primaryLight,
                  child: Text(
                    auth.displayName.isNotEmpty ? auth.displayName[0].toUpperCase() : 'U',
                    style: AppTypography.titleLg.copyWith(color: AppColors.primary),
                  ),
                ),
                const SizedBox(width: AppSpacing.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: AppSpacing.sm,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(auth.displayName, style: AppTypography.sectionTitle),
                          RoleBadge(role: auth.roleDisplay),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.xxs),
                      Text(
                        'Tài khoản: ${user['username'] ?? '—'} · Email: ${user['email'] ?? '—'} · SĐT: ${user['phone_number'] ?? '—'}',
                        style: AppTypography.caption,
                      ),
                    ],
                  ),
                ),
                if (!narrow) ...[
                  const SizedBox(width: AppSpacing.md),
                  actions,
                ],
              ],
            );
            // Điện thoại: nút xuống dưới thông tin thay vì chen cùng hàng.
            if (!narrow) return info;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [info, const SizedBox(height: AppSpacing.md), actions],
            );
          }),
        ),

        // Đơn giá dịch vụ: cấu hình của chủ trọ -> chỉ hiện với vai trò quản lý.
        if (auth.isManager) ...[
        const SizedBox(height: AppSpacing.xxl),

        // Default Utility Rates Card
        AppSurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Đơn giá dịch vụ mặc định',
                style: AppTypography.sectionTitle,
              ),
              const SizedBox(height: 4),
              const Text(
                'Áp dụng khi lập hóa đơn hàng tháng cho các nhà trọ',
                style: AppTypography.caption,
              ),
              const SizedBox(height: 20),
              Wrap(
                spacing: AppSpacing.lg,
                runSpacing: AppSpacing.lg,
                children: [
                  SizedBox(
                    width: 240,
                    child: AppTextField(
                      label: 'Giá điện (VNĐ / kWh)',
                      controller: _elecCtrl,
                      isNumber: true,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: AppTextField(
                      label: 'Giá nước (VNĐ / m³)',
                      controller: _waterCtrl,
                      isNumber: true,
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: AppTextField(
                      label: 'Internet & Rác (VNĐ / phòng)',
                      controller: _netCtrl,
                      isNumber: true,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              // Billing Service chưa có API lưu đơn giá mặc định (nghiệp vụ hóa đơn thuộc Sprint 2):
              // KHÔNG giả lập "lưu thành công" — nút bị vô hiệu hóa và ghi chú rõ ràng.
              const Text(
                'Chưa lưu được: Billing Service chưa có API cấu hình đơn giá (dự kiến Sprint 2). '
                'Đơn giá thực tế được nhập trên từng hóa đơn.',
                key: Key('settings_rate_not_saved_note'),
                style: AppTypography.caption,
              ),
              const SizedBox(height: AppSpacing.md),
              const AppButton(
                key: Key('settings_rate_save'),
                label: 'Lưu cấu hình',
                onPressed: null,
              ),
            ],
          ),
        ),
        ],

      ],
    );
  }
}
