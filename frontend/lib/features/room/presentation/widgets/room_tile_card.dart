import 'package:flutter/material.dart';
import '../../../../core/constants/app_colors.dart';
import '../../../../core/constants/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters.dart';
import '../../../../core/widgets/status_badge.dart';
import '../../../../shared/models/app_models.dart';

/// Stitch Room Tile Card:
/// - Pure white #FFFFFF surface, 16px radius, 1px #E2E8F0 border, Level 1 shadow
/// - 48x48px #EFF6FF leading container with deep blue (#1E3A8A) room code
/// - RoomStatusBadge + #2563EB bold rent price + UI action buttons
class RoomTileCard extends StatefulWidget {
  final RoomItem room;
  final VoidCallback? onTap;
  final VoidCallback? onView;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  const RoomTileCard({
    super.key,
    required this.room,
    this.onTap,
    this.onView,
    this.onEdit,
    this.onDelete,
  });

  @override
  State<RoomTileCard> createState() => _RoomTileCardState();
}

class _RoomTileCardState extends State<RoomTileCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final r = widget.room;
    final shortCode = r.code.replaceFirst(RegExp(r'^P-'), '');

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: widget.onTap != null
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          padding: AppSpacing.cardPadding,
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
            border: Border.all(
              color: _hovered ? AppColors.primaryBorder : AppColors.border,
            ),
            boxShadow: AppSpacing.shadowLevel1,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Header: 48x48 room code box + title + status badge
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: AppColors.primaryLight,
                      borderRadius: BorderRadius.circular(AppSpacing.badgeRadius),
                    ),
                    child: Text(
                      shortCode,
                      style: AppTypography.labelMd.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          r.name,
                          style: AppTypography.titleSm,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          r.propertyName,
                          style: AppTypography.caption,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  StatusBadge.fromRoomStatus(r.status),
                ],
              ),

              const SizedBox(height: AppSpacing.md),

              // Recessed metadata strip
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSpacing.sm,
                ),
                decoration: BoxDecoration(
                  color: AppColors.background,
                  borderRadius: BorderRadius.circular(AppSpacing.badgeRadius),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    _MetaItem(
                      icon: Icons.square_foot_rounded,
                      text: '${AppFormatters.area(r.area)} m²',
                    ),
                    const SizedBox(width: AppSpacing.md),
                    _MetaItem(
                      icon: Icons.people_outline_rounded,
                      text: '${r.currentOccupants}/${r.maxOccupants} người',
                    ),
                    const SizedBox(width: AppSpacing.md),
                    _MetaItem(
                      icon: Icons.layers_outlined,
                      text: 'Tầng ${r.floor}',
                    ),
                  ],
                ),
              ),

              const SizedBox(height: AppSpacing.md),

              // Footer: rent price + actions
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Giá thuê', style: AppTypography.captionSm),
                        Text(
                          '${AppFormatters.currency(r.rentPrice)}/tháng',
                          style: AppTypography.titleMd.copyWith(
                            color: AppColors.secondary,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        tooltip: 'Xem chi tiết',
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(
                          Icons.visibility_outlined,
                          size: 18,
                          color: AppColors.textSecondary,
                        ),
                        onPressed: widget.onView,
                      ),
                      IconButton(
                        tooltip: 'Chỉnh sửa',
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(
                          Icons.edit_outlined,
                          size: 18,
                          color: AppColors.textSecondary,
                        ),
                        onPressed: widget.onEdit,
                      ),
                      IconButton(
                        tooltip: 'Xóa phòng',
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(
                          Icons.delete_outline_rounded,
                          size: 18,
                          color: AppColors.error,
                        ),
                        onPressed: widget.onDelete,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetaItem extends StatelessWidget {
  final IconData icon;
  final String text;

  const _MetaItem({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: AppColors.textSecondary),
          const SizedBox(width: AppSpacing.xs),
          Flexible(
            child: Text(
              text,
              style: AppTypography.labelSm,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
