import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/property_provider.dart';
import '../../models/property_model.dart';
import '../../widgets/custom_text_field.dart';

class PropertyFormScreen extends StatefulWidget {
  final PropertyModel? property;

  const PropertyFormScreen({super.key, this.property});

  @override
  State<PropertyFormScreen> createState() => _PropertyFormScreenState();
}

class _PropertyFormScreenState extends State<PropertyFormScreen> {
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _nameController;
  late TextEditingController _addressController;
  late TextEditingController _wardController;
  late TextEditingController _districtController;
  late TextEditingController _cityController;
  late TextEditingController _floorsController;
  late TextEditingController _electricRateController;
  late TextEditingController _waterRateController;
  late TextEditingController _internetRateController;
  late TextEditingController _rulesController;
  late TextEditingController _descController;

  bool get isEdit => widget.property != null;

  @override
  void initState() {
    super.initState();
    final p = widget.property;
    _nameController = TextEditingController(text: p?.name ?? '');
    _addressController = TextEditingController(text: p?.address ?? '');
    _wardController = TextEditingController(text: p?.ward ?? '');
    _districtController = TextEditingController(text: p?.district ?? '');
    _cityController = TextEditingController(text: p?.city ?? 'TP. Hồ Chí Minh');
    _floorsController = TextEditingController(text: '${p?.totalFloors ?? 1}');
    _electricRateController = TextEditingController(text: '${p?.electricityRate ?? 3500.0}');
    _waterRateController = TextEditingController(text: '${p?.waterRate ?? 20000.0}');
    _internetRateController = TextEditingController(text: '${p?.internetRate ?? 100000.0}');
    _rulesController = TextEditingController(text: p?.rules ?? '');
    _descController = TextEditingController(text: p?.description ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _addressController.dispose();
    _wardController.dispose();
    _districtController.dispose();
    _cityController.dispose();
    _floorsController.dispose();
    _electricRateController.dispose();
    _waterRateController.dispose();
    _internetRateController.dispose();
    _rulesController.dispose();
    _descController.dispose();
    super.dispose();
  }

  Future<void> _handleSave() async {
    if (!_formKey.currentState!.validate()) return;

    final data = {
      'name': _nameController.text.trim(),
      'address': _addressController.text.trim(),
      'ward': _wardController.text.trim(),
      'district': _districtController.text.trim(),
      'city': _cityController.text.trim(),
      'total_floors': int.tryParse(_floorsController.text) ?? 1,
      'electricity_rate': double.tryParse(_electricRateController.text) ?? 3500.0,
      'water_rate': double.tryParse(_waterRateController.text) ?? 20000.0,
      'internet_rate': double.tryParse(_internetRateController.text) ?? 100000.0,
      'rules': _rulesController.text.trim(),
      'description': _descController.text.trim(),
    };

    final provider = Provider.of<PropertyProvider>(context, listen: false);
    bool success;

    if (isEdit) {
      success = await provider.updateProperty(widget.property!.id, data);
    } else {
      success = await provider.createProperty(data);
    }

    if (success && mounted) {
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(isEdit ? 'Đã cập nhật nhà trọ' : 'Tạo mới nhà trọ thành công!'),
          backgroundColor: const Color(0xFF16A34A),
        ),
      );
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(provider.errorMessage ?? 'Thao tác thất bại'),
          backgroundColor: const Color(0xFFDC2626),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<PropertyProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(
          isEdit ? 'Chỉnh Sửa Nhà Trọ' : 'Thêm Nhà Trọ Mới',
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Thông tin chung
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Thông tin chung',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _nameController,
                      label: 'Tên nhà trọ / Tòa nhà *',
                      hint: 'VD: Nhà trọ Hoa Mai, Tòa Happy House',
                      prefixIcon: Icons.apartment_rounded,
                      validator: (v) => (v == null || v.isEmpty) ? 'Vui lòng nhập tên nhà trọ' : null,
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _addressController,
                      label: 'Địa chỉ số nhà, tên đường *',
                      hint: 'VD: 123 Đường Nguyễn Gia Trí',
                      prefixIcon: Icons.location_on_outlined,
                      validator: (v) => (v == null || v.isEmpty) ? 'Vui lòng nhập địa chỉ' : null,
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _wardController,
                            label: 'Phường / Xã',
                            hint: 'VD: Phường 25',
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: CustomTextField(
                            controller: _districtController,
                            label: 'Quận / Huyện',
                            hint: 'VD: Bình Thạnh',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _cityController,
                            label: 'Tỉnh / Thành phố',
                            hint: 'TP. Hồ Chí Minh',
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: CustomTextField(
                            controller: _floorsController,
                            label: 'Số tầng',
                            keyboardType: TextInputType.number,
                            prefixIcon: Icons.layers_outlined,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Biểu phí dịch vụ
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Biểu phí dịch vụ cơ sở',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _electricRateController,
                      label: 'Đơn giá điện (VNĐ/kWh)',
                      hint: '3500',
                      keyboardType: TextInputType.number,
                      prefixIcon: Icons.electric_bolt_rounded,
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _waterRateController,
                      label: 'Đơn giá nước (VNĐ/m³ hoặc người)',
                      hint: '20000',
                      keyboardType: TextInputType.number,
                      prefixIcon: Icons.water_drop_rounded,
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _internetRateController,
                      label: 'Phí Internet / Wifi (VNĐ/phòng/tháng)',
                      hint: '100000',
                      keyboardType: TextInputType.number,
                      prefixIcon: Icons.wifi_rounded,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Nội quy & Tiện ích
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Mô tả & Nội quy chung',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _rulesController,
                      label: 'Nội quy nhà trọ',
                      hint: 'VD: Không làm ồn sau 23h, khóa cổng vân tay...',
                      maxLines: 3,
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _descController,
                      label: 'Mô tả tiện ích chung',
                      hint: 'VD: Camera 24/7, bãi đỗ xe rộng rãi, sân phơi đồ...',
                      maxLines: 3,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: provider.isLoading ? null : _handleSave,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2563EB),
                  padding: const EdgeInsets.symmetric(vertical: 15),
                ),
                child: provider.isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : Text(isEdit ? 'LƯU THAY ĐỔI' : 'TẠO NHÀ TRỌ'),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
