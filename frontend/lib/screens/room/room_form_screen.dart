import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/property_provider.dart';
import '../../models/room_model.dart';
import '../../widgets/custom_text_field.dart';

class RoomFormScreen extends StatefulWidget {
  final int propertyId;
  final RoomModel? room;

  const RoomFormScreen({
    super.key,
    required this.propertyId,
    this.room,
  });

  @override
  State<RoomFormScreen> createState() => _RoomFormScreenState();
}

class _RoomFormScreenState extends State<RoomFormScreen> {
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _roomNumberController;
  late TextEditingController _floorController;
  late TextEditingController _areaController;
  late TextEditingController _rentPriceController;
  late TextEditingController _depositController;
  late TextEditingController _maxOccupantsController;
  late TextEditingController _amenitiesController;
  late TextEditingController _descController;
  late TextEditingController _electricReadingController;
  late TextEditingController _waterReadingController;

  String _status = 'AVAILABLE';

  bool get isEdit => widget.room != null;

  @override
  void initState() {
    super.initState();
    final r = widget.room;
    _roomNumberController = TextEditingController(text: r?.roomNumber ?? '');
    _floorController = TextEditingController(text: '${r?.floor ?? 1}');
    _areaController = TextEditingController(text: '${r?.area ?? 20.0}');
    _rentPriceController = TextEditingController(text: '${r?.rentPrice ?? 3000000.0}');
    _depositController = TextEditingController(text: '${r?.depositAmount ?? 3000000.0}');
    _maxOccupantsController = TextEditingController(text: '${r?.maxOccupants ?? 2}');
    _amenitiesController = TextEditingController(
      text: r?.amenities ?? 'Gác lửng, Máy lạnh, WC riêng',
    );
    _descController = TextEditingController(text: r?.description ?? '');
    _electricReadingController = TextEditingController(text: '${r?.initialElectricReading ?? 0.0}');
    _waterReadingController = TextEditingController(text: '${r?.initialWaterReading ?? 0.0}');

    if (r != null) {
      _status = r.status;
    }
  }

  @override
  void dispose() {
    _roomNumberController.dispose();
    _floorController.dispose();
    _areaController.dispose();
    _rentPriceController.dispose();
    _depositController.dispose();
    _maxOccupantsController.dispose();
    _amenitiesController.dispose();
    _descController.dispose();
    _electricReadingController.dispose();
    _waterReadingController.dispose();
    super.dispose();
  }

  Future<void> _handleSave() async {
    if (!_formKey.currentState!.validate()) return;

    final data = {
      'property': widget.propertyId,
      'room_number': _roomNumberController.text.trim(),
      'floor': int.tryParse(_floorController.text) ?? 1,
      'area': double.tryParse(_areaController.text) ?? 20.0,
      'rent_price': double.tryParse(_rentPriceController.text) ?? 0.0,
      'deposit_amount': double.tryParse(_depositController.text) ?? 0.0,
      'max_occupants': int.tryParse(_maxOccupantsController.text) ?? 2,
      'status': _status,
      'amenities': _amenitiesController.text.trim(),
      'description': _descController.text.trim(),
      'initial_electric_reading': double.tryParse(_electricReadingController.text) ?? 0.0,
      'initial_water_reading': double.tryParse(_waterReadingController.text) ?? 0.0,
    };

    final provider = Provider.of<PropertyProvider>(context, listen: false);
    bool success;

    if (isEdit) {
      success = await provider.updateRoom(widget.room!.id, data);
    } else {
      success = await provider.createRoom(data);
    }

    if (success && mounted) {
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(isEdit ? 'Đã cập nhật phòng thành công' : 'Đã thêm phòng mới thành công!'),
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
          isEdit ? 'Chỉnh Sửa Phòng ${widget.room!.roomNumber}' : 'Thêm Phòng Mới',
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
              // Thông tin định danh & vị trí
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
                      'Thông tin định danh & Vị trí',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _roomNumberController,
                            label: 'Mã / Số phòng *',
                            hint: 'VD: 101, 202',
                            prefixIcon: Icons.door_front_door_outlined,
                            validator: (v) => (v == null || v.isEmpty) ? 'Nhập số phòng' : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: CustomTextField(
                            controller: _floorController,
                            label: 'Tầng số *',
                            hint: 'VD: 1, 2',
                            keyboardType: TextInputType.number,
                            prefixIcon: Icons.layers_outlined,
                            validator: (v) => (v == null || v.isEmpty) ? 'Nhập tầng' : null,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _areaController,
                            label: 'Diện tích (m²)',
                            hint: '25.0',
                            keyboardType: TextInputType.number,
                            prefixIcon: Icons.square_foot_rounded,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: CustomTextField(
                            controller: _maxOccupantsController,
                            label: 'Số người tối đa',
                            hint: '2',
                            keyboardType: TextInputType.number,
                            prefixIcon: Icons.people_outline_rounded,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Giá thuê & Tiền cọc
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
                      'Giá thuê & Tiền cọc',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _rentPriceController,
                      label: 'Giá thuê hàng tháng (VNĐ) *',
                      hint: '3500000',
                      keyboardType: TextInputType.number,
                      prefixIcon: Icons.attach_money_rounded,
                      validator: (v) => (v == null || v.isEmpty) ? 'Nhập giá thuê' : null,
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _depositController,
                      label: 'Tiền đặt cọc (VNĐ)',
                      hint: '3500000',
                      keyboardType: TextInputType.number,
                      prefixIcon: Icons.account_balance_wallet_outlined,
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Trạng thái phòng',
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF334155),
                      ),
                    ),
                    const SizedBox(height: 7),
                    DropdownButtonFormField<String>(
                      initialValue: _status,
                      decoration: InputDecoration(
                        filled: true,
                        fillColor: const Color(0xFFF8FAFC),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                        ),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'AVAILABLE', child: Text('Còn trống (AVAILABLE)')),
                        DropdownMenuItem(value: 'OCCUPIED', child: Text('Đang thuê (OCCUPIED)')),
                        DropdownMenuItem(value: 'RESERVED', child: Text('Đã cọc giữ chỗ (RESERVED)')),
                        DropdownMenuItem(value: 'MAINTENANCE', child: Text('Đang sửa chữa (MAINTENANCE)')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _status = val);
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Tiện nghi & Đồng hồ
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
                      'Tiện nghi & Chỉ số ban đầu',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _amenitiesController,
                      label: 'Tiện nghi phòng',
                      hint: 'VD: Máy lạnh Inverter, Gác lửng, Kệ bếp, Tủ lạnh...',
                      maxLines: 2,
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _electricReadingController,
                            label: 'Điện ban đầu (kWh)',
                            keyboardType: TextInputType.number,
                            prefixIcon: Icons.electric_bolt_rounded,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: CustomTextField(
                            controller: _waterReadingController,
                            label: 'Nước ban đầu (m³)',
                            keyboardType: TextInputType.number,
                            prefixIcon: Icons.water_drop_rounded,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    CustomTextField(
                      controller: _descController,
                      label: 'Ghi chú thêm',
                      hint: 'Ghi chú về tình trạng chìa khóa, hiện trạng phòng...',
                      maxLines: 2,
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
                    : Text(isEdit ? 'LƯU THAY ĐỔI' : 'TẠO PHÒNG'),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
