import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/property_provider.dart';
import '../../models/room_model.dart';
import '../../core/utils/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/status_badge.dart';
import '../../widgets/stat_card.dart';
import '../room/room_detail_screen.dart';
import '../room/room_form_screen.dart';
import 'property_form_screen.dart';

class PropertyDetailScreen extends StatefulWidget {
  final int propertyId;

  const PropertyDetailScreen({super.key, required this.propertyId});

  @override
  State<PropertyDetailScreen> createState() => _PropertyDetailScreenState();
}

class _PropertyDetailScreenState extends State<PropertyDetailScreen> {
  String _selectedStatusFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<PropertyProvider>(context, listen: false)
          .fetchPropertyDetail(widget.propertyId);
    });
  }

  void _onFilterChanged(String filter) {
    setState(() {
      _selectedStatusFilter = filter;
    });
    Provider.of<PropertyProvider>(context, listen: false)
        .fetchRooms(widget.propertyId, statusFilter: filter);
  }

  Future<void> _confirmDeleteProperty() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận xóa nhà trọ?'),
        content: const Text(
          'Toàn bộ phòng trọ và dữ liệu liên quan sẽ bị xóa. Thao tác này không thể hoàn tác.',
        ),
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
          .deleteProperty(widget.propertyId);
      if (success && mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã xóa nhà trọ thành công')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final propertyProvider = Provider.of<PropertyProvider>(context);
    final property = propertyProvider.selectedProperty;
    final rooms = propertyProvider.rooms;
    final stats = propertyProvider.propertyStats;
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;
    final canEdit = user != null && (user.isLandlord || user.isAdmin);

    if (propertyProvider.isLoading && property == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (property == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Chi tiết nhà trọ')),
        body: const Center(child: Text('Không tìm thấy thông tin nhà trọ')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          property.name,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        actions: canEdit
            ? [
                IconButton(
                  icon: const Icon(Icons.edit_outlined),
                  tooltip: 'Chỉnh sửa nhà trọ',
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => PropertyFormScreen(property: property),
                      ),
                    );
                  },
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                  tooltip: 'Xóa nhà trọ',
                  onPressed: _confirmDeleteProperty,
                ),
              ]
            : null,
      ),
      body: RefreshIndicator(
        onRefresh: () => propertyProvider.fetchPropertyDetail(widget.propertyId),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. Info Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.location_on, color: AppTheme.primaryLight, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              property.fullAddress ?? property.address,
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: Color(0xFF1E293B),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Divider(height: 1),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 16,
                        runSpacing: 8,
                        children: [
                          _buildUtilityPill(
                            Icons.electric_bolt,
                            'Điện: ${Formatters.formatCurrency(property.electricityRate)}/kWh',
                            Colors.amber.shade800,
                          ),
                          _buildUtilityPill(
                            Icons.water_drop,
                            'Nước: ${Formatters.formatCurrency(property.waterRate)}/m³',
                            Colors.blue.shade700,
                          ),
                          _buildUtilityPill(
                            Icons.wifi,
                            'Net: ${Formatters.formatCurrency(property.internetRate)}/phòng',
                            Colors.teal.shade700,
                          ),
                        ],
                      ),
                      if (property.description != null && property.description!.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Text(
                          property.description!,
                          style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                        ),
                      ],
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // 2. Stats Overview (Occupancy, Total, Available, Occupied)
              const Text(
                'Thống Kê Phòng',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1E293B)),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: StatCard(
                      title: 'Tổng phòng',
                      value: '${stats?['total_rooms'] ?? property.totalRoomsCount}',
                      icon: Icons.meeting_room_outlined,
                      color: AppTheme.primary,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: StatCard(
                      title: 'Còn trống',
                      value: '${stats?['available_rooms'] ?? property.availableRoomsCount}',
                      icon: Icons.check_circle_outline,
                      color: AppTheme.statusAvailable,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: StatCard(
                      title: 'Đang thuê',
                      value: '${stats?['occupied_rooms'] ?? property.occupiedRoomsCount}',
                      icon: Icons.person_pin_circle_outlined,
                      color: AppTheme.statusOccupied,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 20),

              // 3. Room Filter & Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Danh Sách Phòng Trọ',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1E293B)),
                  ),
                  if (canEdit)
                    TextButton.icon(
                      icon: const Icon(Icons.add, size: 18),
                      label: const Text('Thêm phòng', style: TextStyle(fontWeight: FontWeight.w600)),
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => RoomFormScreen(propertyId: widget.propertyId),
                          ),
                        );
                      },
                    ),
                ],
              ),
              const SizedBox(height: 8),

              // Filter Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildFilterChip('Tất cả', 'ALL'),
                    const SizedBox(width: 6),
                    _buildFilterChip('Còn trống', 'AVAILABLE', color: AppTheme.statusAvailable),
                    const SizedBox(width: 6),
                    _buildFilterChip('Đang thuê', 'OCCUPIED', color: AppTheme.statusOccupied),
                    const SizedBox(width: 6),
                    _buildFilterChip('Đã cọc', 'RESERVED', color: AppTheme.statusReserved),
                    const SizedBox(width: 6),
                    _buildFilterChip('Bảo trì', 'MAINTENANCE', color: AppTheme.statusMaintenance),
                  ],
                ),
              ),

              const SizedBox(height: 14),

              // 4. Room List
              if (rooms.isEmpty)
                Container(
                  padding: const EdgeInsets.all(32),
                  alignment: Alignment.center,
                  child: Column(
                    children: [
                      Icon(Icons.door_sliding_outlined, size: 50, color: Colors.grey.shade400),
                      const SizedBox(height: 8),
                      const Text(
                        'Chưa có phòng nào theo bộ lọc này',
                        style: TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                )
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: rooms.length,
                  itemBuilder: (context, index) {
                    final room = rooms[index];
                    return _buildRoomTile(context, room);
                  },
                ),
            ],
          ),
        ),
      ),
      floatingActionButton: canEdit
          ? FloatingActionButton.extended(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => RoomFormScreen(propertyId: widget.propertyId),
                  ),
                );
              },
              backgroundColor: AppTheme.primary,
              icon: const Icon(Icons.add, color: Colors.white),
              label: const Text('Thêm phòng', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            )
          : null,
    );
  }

  Widget _buildUtilityPill(IconData icon, String text, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 15, color: color),
        const SizedBox(width: 4),
        Text(
          text,
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color),
        ),
      ],
    );
  }

  Widget _buildFilterChip(String label, String value, {Color? color}) {
    final isSelected = _selectedStatusFilter == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => _onFilterChanged(value),
      selectedColor: (color ?? AppTheme.primary).withOpacity(0.18),
      labelStyle: TextStyle(
        fontSize: 12.5,
        fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
        color: isSelected ? (color ?? AppTheme.primary) : const Color(0xFF64748B),
      ),
      backgroundColor: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: isSelected ? (color ?? AppTheme.primary) : const Color(0xFFE2E8F0),
        ),
      ),
    );
  }

  Widget _buildRoomTile(BuildContext context, RoomModel room) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => RoomDetailScreen(
                room: room,
                propertyId: widget.propertyId,
              ),
            ),
          );
        },
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF),
            borderRadius: BorderRadius.circular(12),
          ),
          alignment: Alignment.center,
          child: Text(
            room.roomNumber,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w800,
              color: AppTheme.primary,
            ),
          ),
        ),
        title: Row(
          children: [
            Text(
              'Phòng ${room.roomNumber}',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
            ),
            const SizedBox(width: 8),
            Text(
              '• Tầng ${room.floor}',
              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
            const Spacer(),
            RoomStatusBadge(status: room.status, label: room.statusDisplay),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    Formatters.formatCurrency(room.rentPrice),
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF2563EB),
                    ),
                  ),
                  const Text('/tháng  •  ', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                  Text('${room.area} m²', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                  const Text('  •  ', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                  Text('Tối đa ${room.maxOccupants} người', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                ],
              ),
              if (room.amenities != null && room.amenities!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  'Tiện ích: ${room.amenities}',
                  style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
        trailing: const Icon(Icons.chevron_right, color: Color(0xFF94A3B8)),
      ),
    );
  }
}

