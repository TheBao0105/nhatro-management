import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../models/user_model.dart';
import '../../providers/auth_provider.dart';

enum IdentityFormMode { register, profile, password, createUser, editUser }

class IdentityFormScreen extends StatefulWidget {
  final IdentityFormMode mode;
  final UserModel? user;
  const IdentityFormScreen({super.key, required this.mode, this.user});
  @override
  State<IdentityFormScreen> createState() => _IdentityFormScreenState();
}

class _IdentityFormScreenState extends State<IdentityFormScreen> {
  final _form = GlobalKey<FormState>();
  final Map<String, TextEditingController> _fields = {};
  bool _saving = false;
  String? _error;
  late String _role;
  late bool _active;
  bool get _admin => widget.mode == IdentityFormMode.createUser || widget.mode == IdentityFormMode.editUser;
  bool get _passwordOnly => widget.mode == IdentityFormMode.password;
  bool get _register => widget.mode == IdentityFormMode.register;
  bool get _create => _register || widget.mode == IdentityFormMode.createUser;

  String get _title => switch (widget.mode) {
    IdentityFormMode.register => 'Đăng ký chủ trọ',
    IdentityFormMode.profile => 'Chỉnh sửa hồ sơ',
    IdentityFormMode.password => 'Đổi mật khẩu',
    IdentityFormMode.createUser => 'Tạo tài khoản',
    IdentityFormMode.editUser => 'Sửa tài khoản',
  };

  @override
  void initState() {
    super.initState();
    final data = widget.user?.toJson() ?? <String, dynamic>{};
    for (final key in ['username', 'first_name', 'last_name', 'email', 'phone_number',
      'identity_card', 'address', 'avatar_url', 'password', 'password_confirm', 'old_password', 'new_password']) {
      _fields[key] = TextEditingController(text: data[key]?.toString() ?? '');
    }
    _role = widget.user?.role ?? 'TENANT';
    _active = widget.user?.isActive ?? true;
  }

  @override
  void dispose() {
    for (final field in _fields.values) { field.dispose(); }
    super.dispose();
  }

  Widget _field(String key, String label, {bool secret = false, bool required = false}) =>
    Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: TextFormField(
        controller: _fields[key], obscureText: secret,
        autocorrect: !secret, enableSuggestions: !secret,
        decoration: InputDecoration(labelText: label),
        keyboardType: key == 'email' ? TextInputType.emailAddress : TextInputType.text,
        validator: (value) {
          if (required && (value == null || value.trim().isEmpty)) return 'Vui lòng nhập $label';
          if (key == 'password_confirm' && value != _fields[_passwordOnly ? 'new_password' : 'password']!.text) {
            return 'Mật khẩu xác nhận không khớp';
          }
          return null;
        },
      ),
    );

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _saving = true; _error = null; });
    final auth = context.read<AuthProvider>();
    try {
      bool success = true;
      if (_passwordOnly) {
        success = await auth.changePassword({
          for (final key in ['old_password', 'new_password', 'password_confirm']) key: _fields[key]!.text,
        });
      } else {
        final data = <String, dynamic>{
          for (final key in ['first_name', 'last_name', 'email', 'phone_number', 'identity_card', 'address'])
            key: _fields[key]!.text.trim(),
        };
        if (!_register) {
          final avatar = _fields['avatar_url']!.text.trim();
          data['avatar_url'] = avatar.isEmpty ? null : avatar;
        }
        if (_create || _admin) data['username'] = _fields['username']!.text.trim();
        if (_register) {
          data['password'] = _fields['password']!.text;
          data['password_confirm'] = _fields['password_confirm']!.text;
          success = await auth.register(data);
        } else if (_admin) {
          data['role'] = _role;
          data['is_active'] = _active;
          if (_fields['password']!.text.isNotEmpty) data['password'] = _fields['password']!.text;
          if (widget.mode == IdentityFormMode.createUser) {
            await ApiClient.post(ApiConstants.users, data);
          } else {
            await ApiClient.patch('${ApiConstants.users}${widget.user!.id}/', data);
          }
        } else {
          success = await auth.updateProfile(data);
        }
      }
      if (!mounted) return;
      if (!success) {
        setState(() { _error = auth.errorMessage; });
        return;
      }
      final messenger = ScaffoldMessenger.of(context);
      if (_passwordOnly) {
        Navigator.of(context).popUntil((route) => route.isFirst);
      } else {
        Navigator.of(context).pop(true);
      }
      messenger.showSnackBar(SnackBar(content: Text(_passwordOnly
          ? 'Đã đổi mật khẩu. Hãy đăng nhập lại.'
          : _register ? 'Đăng ký thành công. Bạn có thể đăng nhập.' : 'Đã lưu thông tin.')));
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); });
    } finally {
      if (mounted) setState(() { _saving = false; });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(_title)),
    body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 600),
      child: SingleChildScrollView(padding: const EdgeInsets.all(20),
        child: Form(key: _form, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (_passwordOnly) ...[
            _field('old_password', 'Mật khẩu hiện tại', secret: true, required: true),
            _field('new_password', 'Mật khẩu mới', secret: true, required: true),
            _field('password_confirm', 'Xác nhận mật khẩu mới', secret: true, required: true),
            const Padding(padding: EdgeInsets.only(bottom: 16),
              child: Text('Sau khi đổi mật khẩu, các phiên cũ sẽ không còn sử dụng được.')),
          ] else ...[
            if (_create || _admin) _field('username', 'Tên đăng nhập', required: true),
            if (_create || _admin) _field('password', _create ? 'Mật khẩu' : 'Mật khẩu mới (để trống nếu giữ nguyên)', secret: true, required: _create),
            if (_register) _field('password_confirm', 'Xác nhận mật khẩu', secret: true, required: true),
            _field('first_name', 'Họ và tên đệm'),
            _field('last_name', 'Tên'),
            _field('email', 'Email'),
            _field('phone_number', 'Số điện thoại'),
            _field('identity_card', 'Số CCCD'),
            _field('address', 'Địa chỉ'),
            if (!_register) _field('avatar_url', 'Đường dẫn ảnh đại diện'),
            if (_admin) ...[
              DropdownButtonFormField<String>(initialValue: _role,
                decoration: const InputDecoration(labelText: 'Vai trò'),
                items: const [
                  DropdownMenuItem(value: 'ADMIN', child: Text('Quản trị viên')),
                  DropdownMenuItem(value: 'LANDLORD', child: Text('Chủ trọ')),
                  DropdownMenuItem(value: 'STAFF', child: Text('Nhân viên')),
                  DropdownMenuItem(value: 'TENANT', child: Text('Người thuê')),
                ], onChanged: (value) { if (value != null) setState(() { _role = value; }); }),
              SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Tài khoản đang hoạt động'),
                value: _active, onChanged: (value) => setState(() { _active = value; })),
            ],
          ],
          if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 16),
            child: Text(_error!, style: const TextStyle(color: Colors.red))),
          ElevatedButton(onPressed: _saving ? null : _save,
            child: Text(_saving ? 'Đang lưu...' : _register ? 'ĐĂNG KÝ' : 'LƯU')),
        ])),
      ),
    )),
  );
}
