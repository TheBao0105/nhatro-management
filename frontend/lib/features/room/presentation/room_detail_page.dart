import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_select.dart';
import '../../../core/widgets/app_table.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/page_header.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../shared/models/app_models.dart';
import '../../../shared/services/app_data_repository.dart';

class RoomDetailPage extends StatelessWidget {
  final String roomId;

  const RoomDetailPage({super.key, required this.roomId});

  Future<void> _showRentabilityDialog(
    BuildContext context,
    AppDataRepository repo,
    RoomItem room,
  ) async {
    try {
      final res = await repo.checkRoomRentable(room);
      if (!context.mounted) return;
      final canRent = res['can_rent'] == true;
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Row(
            children: [
              CodeBadge('${res['code'] ?? room.code}'),
              const SizedBox(width: AppSpacing.sm),
              const Expanded(
                child: Text(
                  'Kiểm tra khả năng cho thuê',
                  style: AppTypography.sectionTitle,
                ),
              ),
            ],
          ),
          content: SizedBox(
            width: 460,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: canRent ? AppColors.successLight : AppColors.errorLight,
                    borderRadius: BorderRadius.circular(AppSpacing.badgeRadius),
                    border: Border.all(
                      color: canRent ? AppColors.successBorder : AppColors.errorBorder,
                    ),
                  ),
                  child: Text(
                    canRent
                        ? 'PHÒNG CÓ THỂ CHO THUÊ NGAY'
                        : 'PHÒNG HIỆN KHÔNG THỂ CHO THUÊ',
                    style: AppTypography.bodyBold.copyWith(
                      color: canRent ? AppColors.successText : AppColors.errorText,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                Text('Lý do: ${res['reason'] ?? ''}', style: AppTypography.bodyMd),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Số người: ${res['current_occupants'] ?? room.currentOccupants}/${res['max_occupants'] ?? room.maxOccupants} · Giá: ${AppFormatters.currency(room.rentPrice)}/tháng',
                  style: AppTypography.caption,
                ),
              ],
            ),
          ),
          actions: [
            AppButton(
              label: 'Đóng',
              variant: AppButtonVariant.outlined,
              onPressed: () => Navigator.pop(ctx),
            ),
          ],
        ),
      );
    } catch (e) {
      if (context.mounted) showErrorToast(context, e.toString());
    }
  }

  void _openStatusDialog(
    BuildContext context,
    AppDataRepository repo,
    RoomItem room,
  ) {
    String selectedStatus = room.status;
    final occCtrl = TextEditingController(text: '${room.currentOccupants}');

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => AlertDialog(
          title: Text(
            'Đổi trạng thái ${room.name}',
            style: AppTypography.sectionTitle,
          ),
          content: SizedBox(
            width: 420,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AppSelect<String>(
                  label: 'Trạng thái mới',
                  width: null,
                  value: selectedStatus,
                  options: const [
                    AppSelectOption(value: 'AVAILABLE', label: 'AVAILABLE — Phòng trống'),
                    AppSelectOption(value: 'OCCUPIED', label: 'OCCUPIED — Đang thuê'),
                    AppSelectOption(value: 'FULL', label: 'FULL — Đã đủ người'),
                    AppSelectOption(value: 'RESERVED', label: 'RESERVED — Đã đặt trước'),
                    AppSelectOption(value: 'MAINTENANCE', label: 'MAINTENANCE — Đang bảo trì'),
                    AppSelectOption(value: 'INACTIVE', label: 'INACTIVE — Ngừng hoạt động'),
                  ],
                  onChanged: (v) => setModalState(() => selectedStatus = v ?? room.status),
                ),
                const SizedBox(height: AppSpacing.md),
                AppTextField(
                  label: 'Số người đang ở',
                  controller: occCtrl,
                  isNumber: true,
                ),
              ],
            ),
          ),
          actions: [
            AppButton(
              label: 'Hủy',
              variant: AppButtonVariant.outlined,
              onPressed: () => Navigator.pop(ctx),
            ),
            AppButton(
              label: 'Cập nhật trạng thái',
              onPressed: () async {
                final occ = int.tryParse(occCtrl.text.trim());
                final err = await repo.updateRoomStatus(
                  room.id,
                  selectedStatus,
                  currentOccupants: occ,
                );
                if (!ctx.mounted || !context.mounted) return;
                if (err != null) {
                  showErrorToast(context, err);
                  return;
                }
                Navigator.pop(ctx);
                showSuccessToast(context, 'Đã cập nhật trạng thái phòng ${room.name}.');
              },
            ),
          ],
        ),
      ),
    );
  }

  void _openEditRoomDialog(
    BuildContext context,
    AppDataRepository repo,
    RoomItem room,
  ) {
    final formKey = GlobalKey<FormState>();
    final codeCtrl = TextEditingController(text: room.code);
    final nameCtrl = TextEditingController(text: room.name);
    final floorCtrl = TextEditingController(text: '${room.floor}');
    final priceCtrl = TextEditingController(text: '${room.rentPrice.toInt()}');
    final areaCtrl = TextEditingController(text: AppFormatters.area(room.area));
    final maxCtrl = TextEditingController(text: '${room.maxOccupants}');
    final descCtrl = TextEditingController(text: room.description);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Chỉnh sửa ${room.name}', style: AppTypography.sectionTitle),
        content: SizedBox(
          width: 500,
          child: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: AppTextField(
                          label: 'Mã phòng',
                          controller: codeCtrl,
                          requiredField: true,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: AppTextField(
                          label: 'Tên phòng',
                          controller: nameCtrl,
                          requiredField: true,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    children: [
                      Expanded(
                        child: AppTextField(
                          label: 'Tầng',
                          controller: floorCtrl,
                          requiredField: true,
                          isNumber: true,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: AppTextField(
                          label: 'Giá thuê (VNĐ)',
                          controller: priceCtrl,
                          requiredField: true,
                          isNumber: true,
                          validator: (v) {
                            final raw = v?.trim() ?? '';
                            if (raw.isEmpty) return 'Vui lòng nhập Giá thuê';
                            final n = double.tryParse(raw);
                            if (n == null || n <= 0) return 'Giá thuê phải lớn hơn 0';
                            return null;
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    children: [
                      Expanded(
                        child: AppTextField(
                          label: 'Diện tích (m²)',
                          controller: areaCtrl,
                          requiredField: true,
                          isNumber: true,
                          validator: (v) {
                            final raw = v?.trim() ?? '';
                            if (raw.isEmpty) return 'Vui lòng nhập Diện tích';
                            final n = double.tryParse(raw);
                            if (n == null || n <= 0) return 'Diện tích phải lớn hơn 0';
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: AppTextField(
                          label: 'Số người tối đa',
                          controller: maxCtrl,
                          requiredField: true,
                          isNumber: true,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  AppTextField(
                    label: 'Mô tả',
                    controller: descCtrl,
                    maxLines: 3,
                  ),
                ],
              ),
            ),
          ),
        ),
        actions: [
          AppButton(
            label: 'Hủy',
            variant: AppButtonVariant.outlined,
            onPressed: () => Navigator.pop(ctx),
          ),
          AppButton(
            label: 'Lưu thay đổi',
            onPressed: () async {
              if (!(formKey.currentState?.validate() ?? false)) return;
              final err = await repo.updateRoom(
                room.copyWith(
                  code: codeCtrl.text.trim(),
                  name: nameCtrl.text.trim(),
                  floor: int.tryParse(floorCtrl.text.trim()) ?? room.floor,
                  rentPrice: double.tryParse(priceCtrl.text.trim()) ?? room.rentPrice,
                  area: double.tryParse(areaCtrl.text.trim()) ?? room.area,
                  maxOccupants: int.tryParse(maxCtrl.text.trim()) ?? room.maxOccupants,
                  description: descCtrl.text.trim(),
                ),
              );
              if (!ctx.mounted || !context.mounted) return;
              if (err != null) {
                showErrorToast(context, err);
                return;
              }
              Navigator.pop(ctx);
              showSuccessToast(context, 'Đã cập nhật thông tin phòng ${nameCtrl.text.trim()}.');
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final repo = context.watch<AppDataRepository>();
    final parsedId = int.tryParse(roomId);

    RoomItem? room;
    if (parsedId != null) {
      for (final r in repo.rooms) {
        if (r.id == parsedId) {
          room = r;
          break;
        }
      }
    }

    if (room == null) {
      // Chỉ kết luận "không tìm thấy" khi danh sách phòng đã tải thành công (P4).
      final roomState = repo.sectionState(DataSection.rooms);
      final Widget body;
      final String subtitle;
      if (roomState.isForbidden) {
        subtitle = 'Không có quyền xem thông tin phòng.';
        body = const EmptyState(
          key: Key('room_detail_forbidden'),
          icon: Icons.lock_outline_rounded,
          title: 'Không có quyền xem phòng này',
          subtitle: 'Tài khoản của bạn không được cấp quyền truy cập danh sách phòng.',
        );
      } else if (roomState.isError) {
        subtitle = 'Không tải được thông tin phòng.';
        body = ErrorState(
          key: const Key('room_detail_error'),
          message: 'Không tải được danh sách phòng: ${roomState.message ?? 'lỗi không xác định'}',
          onRetry: repo.syncWithBackend,
        );
      } else if (roomState.isLoading || (repo.isSyncing && !roomState.isLoaded)) {
        subtitle = 'Đang tải thông tin phòng...';
        body = const LoadingState(
          key: Key('room_detail_loading'),
          message: 'Đang tải thông tin phòng...',
        );
      } else if (!roomState.isLoaded) {
        subtitle = 'Chưa tải được thông tin phòng.';
        body = ErrorState(
          key: const Key('room_detail_not_loaded'),
          message: repo.lastSyncError ?? 'Chưa tải được danh sách phòng.',
          onRetry: repo.syncWithBackend,
        );
      } else {
        subtitle = 'Không tìm thấy thông tin phòng theo mã định danh.';
        body = EmptyState(
          key: const Key('room_detail_not_found'),
            icon: Icons.door_front_door_outlined,
            title: 'Không tìm thấy phòng',
            subtitle:
                'Phòng với mã "$roomId" không tồn tại trong dữ liệu hiện tại.',
            actionLabel: 'Quay lại Quản lý phòng',
            onAction: () => context.go('/rooms'),
        );
      }
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeader(
            title: 'Chi tiết phòng',
            subtitle: subtitle,
            actions: [
              AppButton(
                label: 'Quay lại danh sách',
                icon: Icons.arrow_back_rounded,
                variant: AppButtonVariant.outlined,
                onPressed: () => context.go('/rooms'),
              ),
            ],
          ),
          body,
        ],
      );
    }

    final occupancyRatio = room.maxOccupants > 0
        ? (room.currentOccupants / room.maxOccupants).clamp(0.0, 1.0)
        : 0.0;
    final occupancyPercent = (occupancyRatio * 100).round();

    // Ghép theo room_id thật của Contract Service; chỉ so tên khi hợp đồng không có room_id.
    final relatedContracts = repo.contracts
        .where(
          (c) => c.roomId != null
              ? c.roomId == room!.id
              : c.roomName == room!.name && c.propertyName == room.propertyName,
        )
        .toList();
    final contractState = repo.sectionState(DataSection.contracts);
    final String noContractText;
    if (contractState.isForbidden) {
      noContractText = 'Tài khoản của bạn không có quyền xem hợp đồng.';
    } else if (contractState.isError) {
      noContractText = 'Không tải được danh sách hợp đồng: ${contractState.message ?? 'lỗi không xác định'}';
    } else if (contractState.isLoading || (repo.isSyncing && !contractState.isLoaded)) {
      noContractText = 'Đang tải danh sách hợp đồng...';
    } else if (!contractState.isLoaded) {
      noContractText = 'Chưa tải được danh sách hợp đồng.';
    } else {
      noContractText = 'Hiện chưa có hợp đồng nào gắn với phòng này.';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          title: room.name,
          subtitle: '${room.code} · ${room.propertyName}',
          actions: [
            StatusBadge.fromRoomStatus(room.status),
            AppButton(
              label: 'Quay lại',
              icon: Icons.arrow_back_rounded,
              variant: AppButtonVariant.outlined,
              onPressed: () => context.go('/rooms'),
            ),
            AppButton(
              label: 'Kiểm tra cho thuê',
              icon: Icons.fact_check_outlined,
              variant: AppButtonVariant.outlined,
              onPressed: () => _showRentabilityDialog(context, repo, room!),
            ),
            AppButton(
              label: 'Đổi trạng thái',
              icon: Icons.swap_horiz_rounded,
              variant: AppButtonVariant.outlined,
              onPressed: () => _openStatusDialog(context, repo, room!),
            ),
            AppButton(
              label: 'Chỉnh sửa',
              icon: Icons.edit_outlined,
              onPressed: () => _openEditRoomDialog(context, repo, room!),
            ),
          ],
        ),

        // Basic Information & Room Specifications
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth >= 880;

            final basicInfoCard = _DetailSectionCard(
              title: 'Thông tin cơ bản',
              icon: Icons.info_outline_rounded,
              child: Column(
                children: [
                  _KeyValueRow(
                    label: 'Mã phòng',
                    valueWidget: CodeBadge(room!.code),
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Tên phòng',
                    value: room.name,
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Nhà trọ / Tòa nhà',
                    value: room.propertyName,
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Tầng',
                    value: 'Tầng ${room.floor}',
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Trạng thái',
                    valueWidget: StatusBadge.fromRoomStatus(room.status),
                  ),
                ],
              ),
            );

            final specsCard = _DetailSectionCard(
              title: 'Thông số phòng',
              icon: Icons.tune_rounded,
              child: Column(
                children: [
                  _KeyValueRow(
                    label: 'Giá thuê',
                    value: '${AppFormatters.currency(room.rentPrice)}/tháng',
                    valueColor: AppColors.secondary,
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Diện tích',
                    value: '${AppFormatters.area(room.area)} m²',
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Số người hiện tại',
                    value: '${room.currentOccupants} người',
                  ),
                  const Divider(height: 1),
                  _KeyValueRow(
                    label: 'Số người tối đa',
                    value: '${room.maxOccupants} người',
                  ),
                  const Divider(height: 1),
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.md),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'Tỷ lệ sử dụng / phòng',
                              style: AppTypography.bodyMd,
                            ),
                            Text(
                              '$occupancyPercent% (${room.currentOccupants}/${room.maxOccupants})',
                              style: AppTypography.bodyBold.copyWith(
                                color: AppColors.primary,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        ClipRRect(
                          borderRadius:
                              BorderRadius.circular(AppSpacing.pillRadius),
                          child: LinearProgressIndicator(
                            value: occupancyRatio,
                            minHeight: 8,
                            backgroundColor: AppColors.surfaceMuted,
                            valueColor: const AlwaysStoppedAnimation<Color>(
                              AppColors.secondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );

            if (isWide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: basicInfoCard),
                  const SizedBox(width: AppSpacing.lg),
                  Expanded(child: specsCard),
                ],
              );
            }

            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                basicInfoCard,
                const SizedBox(height: AppSpacing.lg),
                specsCard,
              ],
            );
          },
        ),

        const SizedBox(height: AppSpacing.lg),

        // Additional Information
        _DetailSectionCard(
          title: 'Thông tin bổ sung',
          icon: Icons.notes_rounded,
          child: Text(
            room.description.isNotEmpty
                ? room.description
                : 'Chưa có mô tả chi tiết cho phòng này.',
            style: AppTypography.bodyMd,
          ),
        ),

        const SizedBox(height: AppSpacing.lg),

        // Hợp đồng liên quan: lấy từ Contract Service (qua Gateway) trong repository
        AppSurfaceCard(
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.all(AppSpacing.xl),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hợp đồng liên quan',
                      style: AppTypography.sectionTitle,
                    ),
                    SizedBox(height: AppSpacing.xxs),
                    Text(
                      'Danh sách hợp đồng thuê gắn với phòng này',
                      style: AppTypography.caption,
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              if (relatedContracts.isEmpty)
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Text(
                    noContractText,
                    key: const Key('room_detail_contracts_status'),
                    style: AppTypography.caption,
                  ),
                )
              else
                AppTable<ContractItem>(
                  items: relatedContracts,
                  columns: [
                    AppTableColumn(
                      label: 'MÃ HĐ',
                      width: 130,
                      cellBuilder: (c) => CodeBadge(c.code),
                    ),
                    AppTableColumn(
                      label: 'KHÁCH THUÊ ĐẠI DIỆN',
                      flex: 2,
                      cellBuilder: (c) =>
                          Text(c.tenantName, style: AppTypography.bodyBold),
                    ),
                    AppTableColumn(
                      label: 'THỜI HẠN THUÊ',
                      flex: 2,
                      cellBuilder: (c) => Text(
                        '${c.startDate} → ${c.endDate}',
                        style: AppTypography.bodyMd,
                      ),
                    ),
                    AppTableColumn(
                      label: 'GIÁ THỎA THUẬN',
                      width: 150,
                      cellBuilder: (c) => Text(
                        AppFormatters.currency(c.rentPrice),
                        style: AppTypography.bodyBold.copyWith(
                          color: AppColors.secondary,
                        ),
                      ),
                    ),
                    AppTableColumn(
                      label: 'TRẠNG THÁI HĐ',
                      width: 155,
                      cellBuilder: (c) =>
                          StatusBadge.fromContractStatus(c.status),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DetailSectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;

  const _DetailSectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return AppSurfaceCard(
      padding: AppSpacing.cardPadding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 19, color: AppColors.primary),
              const SizedBox(width: AppSpacing.sm),
              Text(title, style: AppTypography.sectionTitle),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          const Divider(height: 1),
          const SizedBox(height: AppSpacing.xs),
          child,
        ],
      ),
    );
  }
}

class _KeyValueRow extends StatelessWidget {
  final String label;
  final String? value;
  final Widget? valueWidget;
  final Color? valueColor;

  const _KeyValueRow({
    required this.label,
    this.value,
    this.valueWidget,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            label,
            style: AppTypography.bodyMd.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(width: AppSpacing.lg),
          Flexible(
            child: valueWidget ??
                Text(
                  value ?? '',
                  textAlign: TextAlign.right,
                  style: AppTypography.bodyBold.copyWith(
                    color: valueColor ?? AppColors.textPrimary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
          ),
        ],
      ),
    );
  }
}
