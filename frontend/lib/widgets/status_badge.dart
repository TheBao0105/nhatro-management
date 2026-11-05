import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

class RoomStatusBadge extends StatelessWidget {
  final String status;
  final String? label;

  const RoomStatusBadge({
    super.key,
    required this.status,
    this.label,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    String text;

    switch (status) {
      case 'AVAILABLE':
        bg = AppTheme.statusAvailable.withOpacity(0.12);
        fg = AppTheme.statusAvailable;
        text = label ?? 'Còn trống';
        break;
      case 'OCCUPIED':
        bg = AppTheme.statusOccupied.withOpacity(0.12);
        fg = AppTheme.statusOccupied;
        text = label ?? 'Đang thuê';
        break;
      case 'MAINTENANCE':
        bg = AppTheme.statusMaintenance.withOpacity(0.15);
        fg = const Color(0xFFD97706);
        text = label ?? 'Bảo trì';
        break;
      case 'RESERVED':
        bg = AppTheme.statusReserved.withOpacity(0.12);
        fg = AppTheme.statusReserved;
        text = label ?? 'Đã cọc';
        break;
      default:
        bg = Colors.grey.withOpacity(0.15);
        fg = Colors.black87;
        text = label ?? status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: fg.withOpacity(0.3), width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              color: fg,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            text,
            style: TextStyle(
              color: fg,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class RoleBadge extends StatelessWidget {
  final String role;
  final String? label;

  const RoleBadge({super.key, required this.role, this.label});

  @override
  Widget build(BuildContext context) {
    Color bg = const Color(0xFFE2E8F0);
    Color fg = const Color(0xFF475569);
    IconData icon = Icons.person_outline;
    String text = label ?? role;

    if (role == 'ADMIN') {
      bg = const Color(0xFFFEE2E2);
      fg = const Color(0xFFDC2626);
      icon = Icons.admin_panel_settings;
      text = label ?? 'Quản trị viên';
    } else if (role == 'LANDLORD') {
      bg = const Color(0xFFE0E7FF);
      fg = const Color(0xFF4338CA);
      icon = Icons.home_work_outlined;
      text = label ?? 'Chủ nhà trọ';
    } else if (role == 'TENANT') {
      bg = const Color(0xFFDCFCE7);
      fg = const Color(0xFF15803D);
      icon = Icons.person;
      text = label ?? 'Khách thuê';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: fg),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              color: fg,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

