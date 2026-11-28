import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/widgets/app_table.dart';
import '../../../core/widgets/page_header.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../shared/models/app_models.dart';
import '../../../shared/services/app_data_repository.dart';
import '../widgets/portal_widgets.dart';

/// TENANT — Phòng đang thuê (chỉ xem). Property Service chỉ trả phòng mà tài khoản này ĐANG thuê
/// (theo liên kết hồ sơ người thuê ở Tenant Service).
class MyRoomPage extends StatelessWidget {
  const MyRoomPage({super.key});

  @override
  Widget build(BuildContext context) {
    final repo = context.watch<AppDataRepository>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          title: 'Phòng đang thuê',
          subtitle: 'Thông tin phòng và nhà trọ bạn đang thuê.',
        ),
        const ReadOnlyNote('Trang chỉ xem. Mọi thay đổi về phòng do chủ trọ thực hiện.'),
        SectionListGate(
          state: repo.sectionState(DataSection.rooms),
          isSyncing: repo.isSyncing,
          lastSyncError: repo.lastSyncError,
          hasData: repo.rooms.isNotEmpty,
          what: 'phòng đang thuê',
          keyPrefix: 'my_room',
          onRetry: repo.syncWithBackend,
          empty: const EmptyState(
            key: Key('my_room_empty'),
            icon: Icons.door_front_door_outlined,
            title: 'Bạn chưa có phòng đang thuê',
            subtitle: 'Khi chủ trọ liên kết hồ sơ người thuê với tài khoản của bạn, phòng sẽ hiển thị ở đây.',
          ),
          noMatch: null,
          builder: (_) => Column(
            children: [
              for (final room in repo.rooms) ...[
                _RoomCard(
                  room: room,
                  property: repo.properties.where((p) => p.id == room.propertyId).firstOrNull,
                ),
                const SizedBox(height: AppSpacing.lg),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _RoomCard extends StatelessWidget {
  final RoomItem room;
  final PropertyItem? property;

  const _RoomCard({required this.room, required this.property});

  @override
  Widget build(BuildContext context) {
    return AppSurfaceCard(
      key: Key('my_room_card_${room.id}'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              CodeBadge(room.code),
              Text(room.name, style: AppTypography.sectionTitle),
              StatusBadge.fromRoomStatus(room.status),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          InfoRow('Nhà trọ', property?.name ?? room.propertyName),
          InfoRow('Địa chỉ', property?.displayAddress ?? ''),
          InfoRow('Tầng', '${room.floor}'),
          InfoRow('Diện tích', room.area > 0 ? '${AppFormatters.area(room.area)} m²' : ''),
          InfoRow('Giá thuê / tháng', AppFormatters.currency(room.rentPrice)),
          InfoRow('Số người ở', '${room.currentOccupants}/${room.maxOccupants}'),
          if (room.description.isNotEmpty) InfoRow('Mô tả', room.description),
          // Identity Service không cho TENANT xem tài khoản khác nên chưa có thông tin liên hệ chủ trọ.
          const InfoRow('Liên hệ chủ trọ', 'Hệ thống chưa cung cấp thông tin liên hệ chủ trọ cho khách thuê.'),
        ],
      ),
    );
  }
}
