import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/status_badge.dart';
import 'identity_form_screen.dart';
import 'users_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;
    if (user == null) return const SizedBox.shrink();
    return Scaffold(
      appBar: AppBar(title: const Text('Tài khoản')),
      body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 700),
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text(user.displayName, style: Theme.of(context).textTheme.headlineSmall),
          Text('@${user.username}'),
          const SizedBox(height: 12),
          Align(alignment: Alignment.centerLeft, child: RoleBadge(role: user.role, label: user.roleDisplay)),
          const SizedBox(height: 16),
          for (final item in <String, String?>{
            'Email': user.email, 'Số điện thoại': user.phoneNumber,
            'CCCD': user.identityCard, 'Địa chỉ': user.address,
          }.entries)
            ListTile(contentPadding: EdgeInsets.zero, title: Text(item.key),
              subtitle: Text(item.value?.isNotEmpty == true ? item.value! : 'Chưa cập nhật')),
          const Divider(),
          ListTile(leading: const Icon(Icons.edit_outlined), title: const Text('Chỉnh sửa hồ sơ'),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) =>
              IdentityFormScreen(mode: IdentityFormMode.profile, user: user)))),
          ListTile(leading: const Icon(Icons.password), title: const Text('Đổi mật khẩu'),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) =>
              const IdentityFormScreen(mode: IdentityFormMode.password)))),
          if (user.isAdmin) ListTile(leading: const Icon(Icons.manage_accounts_outlined),
            title: const Text('Quản lý tài khoản và phân quyền'),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const UsersScreen()))),
          ListTile(leading: const Icon(Icons.logout, color: Colors.red), title: const Text('Đăng xuất'),
            onTap: () async {
              final confirmed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
                title: const Text('Đăng xuất tài khoản?'), actions: [
                  TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('HỦY')),
                  TextButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('ĐĂNG XUẤT')),
                ]));
              if (confirmed == true) await auth.logout();
            }),
        ]),
      )),
    );
  }
}
