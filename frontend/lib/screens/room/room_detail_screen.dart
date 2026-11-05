import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/property_provider.dart';
import '../../models/room_model.dart';
import '../../core/utils/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/status_badge.dart';
import 'room_form_screen.dart';

class RoomDetailScreen extends StatefulWidget {
  final RoomModel room;
  final int propertyId;

  const RoomDetailScreen({
    super.key,
    required this.room,
    required this.propertyId,
  });

  @override
  State<RoomDetailScreen> createState() => _RoomDetailScreenState();
}

class _RoomDetailScreenState extends State<RoomDetailScreen> {
  late RoomModel _currentRoom;

  @override
  void initState() {
    super.initState();
    _currentRoom = widget.room;
  }

  Future<void> _changeStatus(String newStatus) async {
    final success = await Provider.of<PropertyProvider>(context, listen: false)
        .updateRoomStatus(_currentRoom.id, newStatus);
    if (success && mounted) {
      setState(() {
        _currentRoom = Provider.of<PropertyProvider>(context, listen: false)
            .rooms
            .firstWhere((r) => r.id == _currentRoom.id, orElse: () => _currentRoom);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã cập nhật trạng thái phòng thành công!')),
      );
    }
  }

  Future<void> _confirmDeleteRoom() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Xác nhận xóa Phòng ${_currentRoom.roomNumber}?'),
        content: const Text('Thao tác này sẽ xóa vĩnh viễn phòng này khỏi hệ thống.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('HỦY'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('XÓA'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final success = await Provider.of<PropertyProvider>(context, listen: false)
          .deleteRoom(_currentRoom.id);
      if (success && mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã xóa phòng thành công')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;
    final canEdit = user != null && (user.isLandlord || user.isAdmin);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Phòng ${_currentRoom.roomNumber}',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        actions: canEdit
            ? [
                IconButton(
                  icon: const Icon(Icons.edit_outlined),
                  tooltip: 'Chỉnh sửa phòng',
                  onPressed: () async {
                    final provider = Provider.of<PropertyProvider>(context, listen: false);
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => RoomFormScreen(
                          propertyId: widget.propertyId,
                          room: _currentRoom,
                        ),
                      ),
                    );
                    if (!mounted) return;
                    final updated = provider.rooms
                        .firstWhere((r) => r.id == _currentRoom.id, orElse: () => _currentRoom);
                    setState(() {
                      _currentRoom = updated;
                    });
                  },
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                  tooltip: 'Xóa phòng',
                  onPressed: _confirmDeleteRoom,
                ),
              ]
            : null,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status Header
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      _currentRoom.roomNumber,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Tầng ${_currentRoom.floor} • Diện tích ${_currentRoom.area} m²',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF334155),
                          ),
                        ),
                        const SizedBox(height: 6),
                        RoomStatusBadge(
                          status: _currentRoom.status,
                          label: _currentRoom.statusDisplay,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Quick Status Switcher (For Landlord/Admin)
            if (canEdit) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Chuyển nhanh trạng thái phòng',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _buildStatusButton('Còn trống', 'AVAILABLE', AppTheme.statusAvailable),
                          _buildStatusButton('Đang thuê', 'OCCUPIED', AppTheme.statusOccupied),
                          _buildStatusButton('Đã cọc', 'RESERVED', AppTheme.statusReserved),
                          _buildStatusButton('Bảo trì', 'MAINTENANCE', AppTheme.statusMaintenance),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Pricing Info Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Chi phí thuê & Tiền cọc',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 14),
                    _buildInfoRow(
                      'Giá thuê hàng tháng',
                      Formatters.formatCurrency(_currentRoom.rentPrice),
                      isHighlight: true,
                    ),
                    const Divider(height: 16),
                    _buildInfoRow(
                      'Tiền đặt cọc',
                      Formatters.formatCurrency(_currentRoom.depositAmount),
                    ),
                    const Divider(height: 16),
                    _buildInfoRow(
                      'Số người ở tối đa',
                      '${_currentRoom.maxOccupants} người',
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Amenities & Details
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Tiện nghi & Thiết bị trong phòng',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      (_currentRoom.amenities != null && _currentRoom.amenities!.isNotEmpty)
                          ? _currentRoom.amenities!
                          : 'Chưa cập nhật tiện nghi',
                      style: const TextStyle(fontSize: 14, color: Color(0xFF475569)),
                    ),
                    if (_currentRoom.description != null && _currentRoom.description!.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      const Text(
                        'Ghi chú / Mô tả thêm:',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF64748B)),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _currentRoom.description!,
                        style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Initial Meters
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Chỉ số đồng hồ ban đầu',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 14),
                    _buildInfoRow('Chỉ số điện ban đầu', '${_currentRoom.initialElectricReading} kWh'),
                    const Divider(height: 16),
                    _buildInfoRow('Chỉ số nước ban đầu', '${_currentRoom.initialWaterReading} m³'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusButton(String label, String statusKey, Color color) {
    final isCurrent = _currentRoom.status == statusKey;
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        backgroundColor: isCurrent ? color.withOpacity(0.15) : Colors.transparent,
        side: BorderSide(color: isCurrent ? color : const Color(0xFFCBD5E1), width: isCurrent ? 1.5 : 1.0),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
      onPressed: isCurrent ? null : () => _changeStatus(statusKey),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isCurrent) ...[
            Icon(Icons.check, size: 14, color: color),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: isCurrent ? FontWeight.w700 : FontWeight.w500,
              color: isCurrent ? color : const Color(0xFF475569),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {bool isHighlight = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 13.5, color: Color(0xFF64748B)),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: isHighlight ? 16 : 14,
            fontWeight: isHighlight ? FontWeight.w800 : FontWeight.w600,
            color: isHighlight ? const Color(0xFF2563EB) : const Color(0xFF1E293B),
          ),
        ),
      ],
    );
  }
}
