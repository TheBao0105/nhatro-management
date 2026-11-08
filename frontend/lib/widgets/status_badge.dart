import 'package:flutter/material.dart';

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
        bg = const Color(0xFFDCFCE7);
        fg = const Color(0xFF15803D);
        text = label ?? 'Còn trống';
        break;
      case 'OCCUPIED':
        bg = const Color(0xFFFEE2E2);
        fg = const Color(0xFFB91C1C);
        text = label ?? 'Đang thuê';
        break;
      case 'MAINTENANCE':
        bg = const Color(0xFFFEF3C7);
        fg = const Color(0xFFB45309);
        text = label ?? 'Bảo trì';
        break;
      case 'RESERVED':
        bg = const Color(0xFFEDE9FE);
        fg = const Color(0xFF6D28D9);
        text = label ?? 'Đã cọc';
        break;
      default:
        bg = const Color(0xFFF1F5F9);
        fg = const Color(0xFF475569);
        text = label ?? status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
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
              fontWeight: FontWeight.w700,
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
    Color bg = const Color(0xFFF1F5F9);
    Color fg = const Color(0xFF475569);
    IconData icon = Icons.person_outline;
    String text = label ?? role;

    if (role == 'ADMIN') {
      bg = const Color(0xFFFEE2E2);
      fg = const Color(0xFFDC2626);
      icon = Icons.admin_panel_settings_rounded;
      text = label ?? 'Quản trị viên';
    } else if (role == 'LANDLORD') {
      bg = const Color(0xFFEFF6FF);
      fg = const Color(0xFF1D4ED8);
      icon = Icons.home_work_rounded;
      text = label ?? 'Chủ nhà trọ';
    } else if (role == 'TENANT') {
      bg = const Color(0xFFDCFCE7);
      fg = const Color(0xFF15803D);
      icon = Icons.person_rounded;
      text = label ?? 'Khách thuê';
    } else if (role == 'STAFF') {
      bg = const Color(0xFFFEF3C7);
      fg = const Color(0xFFD97706);
      icon = Icons.badge_rounded;
      text = label ?? 'Nhân viên';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: fg),
          const SizedBox(width: 5),
          Text(
            text,
            style: TextStyle(
              color: fg,
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
