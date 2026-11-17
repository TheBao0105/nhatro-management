import 'package:flutter/material.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../models/user_model.dart';
import 'identity_form_screen.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});
  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  final _search = TextEditingController();
  List<UserModel> _users = [];
  bool _loading = true;
  String? _error;
  int _requestId = 0;

  @override
  void initState() { super.initState(); _load(); }
  @override
  void dispose() { _search.dispose(); super.dispose(); }

  Future<void> _load() async {
    final requestId = ++_requestId;
    setState(() { _loading = true; _error = null; });
    try {
      final response = await ApiClient.get('${ApiConstants.users}?search=${Uri.encodeQueryComponent(_search.text.trim())}');
      if (!mounted || requestId != _requestId) return;
      setState(() { _users = (response as List).map((item) => UserModel.fromJson(item as Map<String, dynamic>)).toList(); });
    } catch (e) {
      if (mounted && requestId == _requestId) setState(() { _error = e.toString(); });
    } finally {
      if (mounted && requestId == _requestId) setState(() { _loading = false; });
    }
  }

  Future<void> _edit([UserModel? user]) async {
    final changed = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) =>
      IdentityFormScreen(mode: user == null ? IdentityFormMode.createUser : IdentityFormMode.editUser, user: user)));
    if (changed == true && mounted) await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Quản lý tài khoản'), actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))]),
    body: Column(children: [
      Padding(padding: const EdgeInsets.all(16), child: TextField(controller: _search,
        decoration: InputDecoration(labelText: 'Tên đăng nhập, email hoặc số điện thoại',
          suffixIcon: IconButton(icon: const Icon(Icons.search), onPressed: _load)), onSubmitted: (_) => _load())),
      if (_loading) const LinearProgressIndicator(),
      if (_error != null) Padding(padding: const EdgeInsets.all(16), child: Text(_error!, style: const TextStyle(color: Colors.red))),
      Expanded(child: _users.isEmpty && !_loading
        ? const Center(child: Text('Không có tài khoản phù hợp.'))
        : ListView.builder(itemCount: _users.length, itemBuilder: (context, index) {
            final user = _users[index];
            return ListTile(title: Text('${user.displayName} (@${user.username})'),
              subtitle: Text('${user.roleDisplay ?? user.role} • ${user.isActive ? 'Đang hoạt động' : 'Đã khóa'}'),
              trailing: const Icon(Icons.edit_outlined), onTap: () => _edit(user));
          })),
    ]),
    floatingActionButton: FloatingActionButton(onPressed: () => _edit(), child: const Icon(Icons.person_add)),
  );
}
