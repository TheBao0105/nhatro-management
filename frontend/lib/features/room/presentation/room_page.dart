import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_search_bar.dart';
import '../../../core/widgets/app_select.dart';
import '../../../core/widgets/app_table.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/confirm_dialog.dart';
import '../../../core/widgets/page_header.dart';
import '../../../core/widgets/pagination_widget.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../shared/models/app_models.dart';
import '../../../shared/services/app_data_repository.dart';
import 'widgets/room_tile_card.dart';

class RoomPage extends StatefulWidget {
  const RoomPage({super.key});

  @override
  State<RoomPage> createState() => _RoomPageState();
}

class _RoomPageState extends State<RoomPage> {
  final _searchCtrl = TextEditingController();
  String _propertyFilter = 'ALL';
  String _statusFilter = 'ALL';
  String _priceFilter = 'ALL';
  String _sortBy = 'DEFAULT';
  bool _isGridView = false;
  int _page = 1;
  static const int _pageSize = 6;

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  void _openRoomForm([RoomItem? existing]) {
    final repo = context.read<AppDataRepository>();
    if (repo.properties.isEmpty) {
      showErrorToast(context, 'Vui lòng tạo nhà trọ trước khi thêm phòng.');
      return;
    }

    final formKey = GlobalKey<FormState>();
    int propertyId = existing?.propertyId ?? repo.properties.first.id;
    final codeCtrl = TextEditingController(
      text: existing?.code ?? 'P-A${100 + repo.rooms.length + 1}',
    );
    final nameCtrl = TextEditingController(
      text: existing?.name ?? 'Phòng A${100 + repo.rooms.length + 1}',
    );
    final priceCtrl = TextEditingController(
      text: '${existing?.rentPrice.toInt() ?? 3500000}',
    );
    final areaCtrl = TextEditingController(
      text: AppFormatters.area(existing?.area ?? 22),
    );
    final currOccCtrl = TextEditingController(
      text: '${existing?.currentOccupants ?? 0}',
    );
    final maxOccCtrl = TextEditingController(
      text: '${existing?.maxOccupants ?? 2}',
    );
    final descCtrl = TextEditingController(text: existing?.description ?? '');
    String status = existing?.status ?? 'AVAILABLE';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => AlertDialog(
          title: Text(
            existing == null ? 'Thêm phòng mới' : 'Chỉnh sửa thông tin phòng',
            style: AppTypography.sectionTitle,
          ),
          content: SizedBox(
            width: 540,
            child: Form(
              key: formKey,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    AppSelect<int>(
                      label: 'Thuộc nhà trọ',
                      width: null,
                      value: propertyId,
                      options: [
                        for (final p in repo.properties)
                          AppSelectOption(value: p.id, label: '${p.code} — ${p.name}'),
                      ],
                      onChanged: (v) =>
                          setModalState(() => propertyId = v ?? repo.properties.first.id),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: AppTextField(
                            label: 'Mã phòng',
                            controller: codeCtrl,
                            requiredField: true,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: AppTextField(
                            label: 'Tên phòng',
                            controller: nameCtrl,
                            requiredField: true,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: AppTextField(
                            label: 'Giá thuê (VNĐ/tháng)',
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
                        const SizedBox(width: 12),
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
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: AppTextField(
                            label: 'Số người hiện tại',
                            controller: currOccCtrl,
                            requiredField: true,
                            isNumber: true,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: AppTextField(
                            label: 'Số người tối đa',
                            controller: maxOccCtrl,
                            requiredField: true,
                            isNumber: true,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    AppSelect<String>(
                      label: 'Trạng thái phòng',
                      width: null,
                      value: status,
                      options: const [
                        AppSelectOption(value: 'AVAILABLE', label: 'Còn trống'),
                        AppSelectOption(value: 'OCCUPIED', label: 'Đang thuê'),
                        AppSelectOption(value: 'FULL', label: 'Đã đủ người'),
                        AppSelectOption(value: 'RESERVED', label: 'Đã đặt trước'),
                        AppSelectOption(value: 'MAINTENANCE', label: 'Đang bảo trì'),
                        AppSelectOption(value: 'INACTIVE', label: 'Ngừng hoạt động'),
                      ],
                      onChanged: (v) => setModalState(() => status = v ?? 'AVAILABLE'),
                    ),
                    const SizedBox(height: 14),
                    AppTextField(
                      label: 'Mô tả tiện nghi phòng',
                      controller: descCtrl,
                      maxLines: 2,
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
              label: existing == null ? 'Thêm phòng' : 'Lưu thay đổi',
              onPressed: () async {
                if (!formKey.currentState!.validate()) return;
                final prop = repo.properties.firstWhere((p) => p.id == propertyId);
                final price = double.tryParse(priceCtrl.text.trim()) ?? 0;
                final area = double.tryParse(areaCtrl.text.trim()) ?? 20;
                final curr = int.tryParse(currOccCtrl.text.trim()) ?? 0;
                final max = int.tryParse(maxOccCtrl.text.trim()) ?? 2;

                if (existing == null) {
                  final err = await repo.addRoom(
                    RoomItem(
                      id: DateTime.now().millisecondsSinceEpoch,
                      code: codeCtrl.text.trim(),
                      name: nameCtrl.text.trim(),
                      propertyId: prop.id,
                      propertyName: prop.name,
                      rentPrice: price,
                      area: area,
                      currentOccupants: curr,
                      maxOccupants: max,
                      status: status,
                      description: descCtrl.text.trim(),
                    ),
                  );
                  if (!ctx.mounted || !mounted) return;
                  if (err != null) {
                    showErrorToast(context, err);
                    return;
                  }
                  Navigator.pop(ctx);
                  showSuccessToast(context, 'Đã thêm "${nameCtrl.text.trim()}"');
                } else {
                  final err = await repo.updateRoom(
                    existing.copyWith(
                      code: codeCtrl.text.trim(),
                      name: nameCtrl.text.trim(),
                      propertyId: prop.id,
                      propertyName: prop.name,
                      rentPrice: price,
                      area: area,
                      currentOccupants: curr,
                      maxOccupants: max,
                      status: status,
                      description: descCtrl.text.trim(),
                    ),
                  );
                  if (!ctx.mounted || !mounted) return;
                  if (err != null) {
                    showErrorToast(context, err);
                    return;
                  }
                  Navigator.pop(ctx);
                  showSuccessToast(context, 'Đã cập nhật "${nameCtrl.text.trim()}"');
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmDelete(RoomItem room) async {
    final confirmed = await ConfirmDialog.show(
      context,
      title: 'Xác nhận xóa phòng',
      message: 'Bạn có chắc chắn muốn xóa ${room.name} (${room.code}) khỏi ${room.propertyName}?',
    );
    if (!confirmed || !mounted) return;
    final err = await context.read<AppDataRepository>().deleteRoom(room.id);
    if (!mounted) return;
    if (err != null) {
      showErrorToast(context, err);
      return;
    }
    showSuccessToast(context, 'Đã xóa ${room.name}');
  }

  @override
  Widget build(BuildContext context) {
    final repo = context.watch<AppDataRepository>();
    final query = _searchCtrl.text.trim().toLowerCase();
    final roomState = repo.sectionState(DataSection.rooms);

    // Nhà trọ đang lọc có thể vừa bị xóa / ra khỏi phạm vi sau khi đồng bộ: quay về "Tất cả"
    // (giá trị không có trong danh sách lựa chọn sẽ làm hỏng ô chọn).
    final propertyFilter = _propertyFilter == 'ALL' ||
            repo.properties.any((p) => '${p.id}' == _propertyFilter)
        ? _propertyFilter
        : 'ALL';

    final filtered = repo.rooms.where((r) {
      final matchesProp =
          propertyFilter == 'ALL' || '${r.propertyId}' == propertyFilter;
      final matchesStatus = _statusFilter == 'ALL' || r.status == _statusFilter;
      final matchesPrice = switch (_priceFilter) {
        'UNDER_3M' => r.rentPrice < 3000000,
        '3M_TO_4M' => r.rentPrice >= 3000000 && r.rentPrice <= 4000000,
        'OVER_4M' => r.rentPrice > 4000000,
        _ => true,
      };
      final matchesQuery = query.isEmpty ||
          r.name.toLowerCase().contains(query) ||
          r.code.toLowerCase().contains(query) ||
          r.propertyName.toLowerCase().contains(query);
      return matchesProp && matchesStatus && matchesPrice && matchesQuery;
    }).toList();

    switch (_sortBy) {
      case 'price_asc':
        filtered.sort((a, b) => a.rentPrice.compareTo(b.rentPrice));
      case 'price_desc':
        filtered.sort((a, b) => b.rentPrice.compareTo(a.rentPrice));
      case 'area_asc':
        filtered.sort((a, b) => a.area.compareTo(b.area));
      case 'area_desc':
        filtered.sort((a, b) => b.area.compareTo(a.area));
      case 'name_asc':
        filtered.sort((a, b) => a.name.compareTo(b.name));
    }

    // Sau khi xóa / lọc, số trang có thể giảm: không để trang hiện tại vượt quá trang cuối.
    final pageCount = filtered.isEmpty ? 1 : (filtered.length + _pageSize - 1) ~/ _pageSize;
    final page = _page.clamp(1, pageCount);
    final start = ((page - 1) * _pageSize).clamp(0, filtered.length);
    final end = (page * _pageSize).clamp(0, filtered.length);
    final paged = filtered.sublist(start, end);
    final hasFilter = query.isNotEmpty ||
        propertyFilter != 'ALL' ||
        _statusFilter != 'ALL' ||
        _priceFilter != 'ALL';
    void resetFilters() => setState(() {
          _searchCtrl.clear();
          _propertyFilter = 'ALL';
          _statusFilter = 'ALL';
          _priceFilter = 'ALL';
          _sortBy = 'DEFAULT';
          _page = 1;
        });

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          title: 'Quản lý phòng',
          subtitle: 'Theo dõi trạng thái phòng trống, đang thuê, diện tích và đơn giá thuê.',
          actions: [
            _ViewModeToggle(
              isGridView: _isGridView,
              onChanged: (grid) => setState(() => _isGridView = grid),
            ),
            AppButton(
              label: '+ Thêm phòng',
              onPressed: () => context.go('/rooms/create'),
            ),
          ],
        ),

        // Search & Filters Bar
        AppSurfaceCard(
          padding: AppSpacing.cardPadding,
          child: Wrap(
            spacing: AppSpacing.md,
            runSpacing: AppSpacing.md,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              AppSearchBar(
                controller: _searchCtrl,
                hintText: 'Tìm theo tên phòng, mã phòng...',
                onChanged: (_) => setState(() => _page = 1),
              ),
              AppSelect<String>(
                label: 'Tòa nhà / Nhà trọ',
                width: 230,
                value: propertyFilter,
                options: [
                  const AppSelectOption(value: 'ALL', label: 'Tất cả tòa nhà'),
                  for (final p in repo.properties)
                    AppSelectOption(value: '${p.id}', label: p.name),
                ],
                onChanged: (v) => setState(() {
                  _propertyFilter = v ?? 'ALL';
                  _page = 1;
                }),
              ),
              AppSelect<String>(
                label: 'Trạng thái',
                width: 175,
                value: _statusFilter,
                options: const [
                  AppSelectOption(value: 'ALL', label: 'Tất cả trạng thái'),
                  AppSelectOption(value: 'AVAILABLE', label: 'Còn trống'),
                  AppSelectOption(value: 'OCCUPIED', label: 'Đang thuê'),
                  AppSelectOption(value: 'FULL', label: 'Đã đủ người'),
                  AppSelectOption(value: 'RESERVED', label: 'Đã đặt trước'),
                  AppSelectOption(value: 'MAINTENANCE', label: 'Đang bảo trì'),
                  AppSelectOption(value: 'INACTIVE', label: 'Ngừng hoạt động'),
                ],
                onChanged: (v) => setState(() {
                  _statusFilter = v ?? 'ALL';
                  _page = 1;
                }),
              ),
              AppSelect<String>(
                label: 'Mức giá',
                width: 185,
                value: _priceFilter,
                options: const [
                  AppSelectOption(value: 'ALL', label: 'Tất cả mức giá'),
                  AppSelectOption(value: 'UNDER_3M', label: 'Dưới 3.000.000 đ'),
                  AppSelectOption(value: '3M_TO_4M', label: '3.000.000 – 4.000.000 đ'),
                  AppSelectOption(value: 'OVER_4M', label: 'Trên 4.000.000 đ'),
                ],
                onChanged: (v) => setState(() {
                  _priceFilter = v ?? 'ALL';
                  _page = 1;
                }),
              ),
              AppSelect<String>(
                label: 'Sắp xếp',
                width: 180,
                value: _sortBy,
                options: const [
                  AppSelectOption(value: 'DEFAULT', label: 'Mặc định'),
                  AppSelectOption(value: 'price_asc', label: 'Giá tăng dần ↑'),
                  AppSelectOption(value: 'price_desc', label: 'Giá giảm dần ↓'),
                  AppSelectOption(value: 'area_asc', label: 'Diện tích tăng dần ↑'),
                  AppSelectOption(value: 'area_desc', label: 'Diện tích giảm dần ↓'),
                  AppSelectOption(value: 'name_asc', label: 'Tên phòng (A → Z)'),
                ],
                onChanged: (v) => setState(() {
                  _sortBy = v ?? 'DEFAULT';
                  _page = 1;
                }),
              ),
              if (hasFilter || _sortBy != 'DEFAULT')
                AppButton(
                  label: 'Đặt lại',
                  variant: AppButtonVariant.outlined,
                  compact: true,
                  onPressed: resetFilters,
                ),
            ],
          ),
        ),

        const SizedBox(height: AppSpacing.lg),

        if (repo.rooms.isNotEmpty && roomState.isError)
          StaleDataBanner(
            key: const Key('room_list_stale'),
            message: 'Không cập nhật được danh sách phòng: ${roomState.message ?? 'lỗi không xác định'}. '
                'Đang hiển thị dữ liệu của lần tải trước.',
            onRetry: repo.syncWithBackend,
          ),
        if (repo.rooms.isEmpty && roomState.isForbidden)
          const EmptyState(
            key: Key('room_list_forbidden'),
            icon: Icons.lock_outline_rounded,
            title: 'Không có quyền xem danh sách phòng',
            subtitle: 'Tài khoản của bạn không được cấp quyền truy cập dữ liệu này.',
          )
        else if (repo.rooms.isEmpty && roomState.isError)
          ErrorState(
            key: const Key('room_list_error'),
            message: 'Không tải được danh sách phòng: ${roomState.message ?? 'lỗi không xác định'}',
            onRetry: repo.syncWithBackend,
          )
        else if (repo.rooms.isEmpty && (roomState.isLoading || (repo.isSyncing && !roomState.isLoaded)))
          const LoadingState(
            key: Key('room_list_loading'),
            message: 'Đang tải danh sách phòng...',
          )
        else if (repo.rooms.isEmpty && !roomState.isLoaded)
          // Chưa tải và không có lượt tải nào đang chạy: không giả vờ "đang tải", không nói "rỗng".
          ErrorState(
            key: const Key('room_list_not_loaded'),
            message: repo.lastSyncError ?? 'Chưa tải được danh sách phòng.',
            onRetry: repo.syncWithBackend,
          )
        else if (repo.rooms.isEmpty)
          EmptyState(
            key: const Key('room_list_empty'),
            icon: Icons.door_front_door_outlined,
            title: 'Chưa có phòng nào',
            subtitle: 'Hệ thống chưa có phòng nào trong phạm vi quản lý của bạn.',
            actionLabel: '+ Thêm phòng',
            onAction: () => context.go('/rooms/create'),
          )
        else if (filtered.isEmpty)
          EmptyState(
            key: const Key('room_list_no_match'),
            icon: Icons.search_off_rounded,
            title: 'Không có phòng nào phù hợp',
            subtitle: 'Không có phòng nào khớp với từ khóa hoặc bộ lọc hiện tại.',
            actionLabel: hasFilter ? 'Đặt lại bộ lọc' : null,
            onAction: hasFilter ? resetFilters : null,
          )
        else if (_isGridView) ...[
          LayoutBuilder(
            builder: (context, constraints) {
              final w = constraints.maxWidth;
              final crossAxisCount = w >= 1080 ? 3 : (w >= 660 ? 2 : 1);
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: paged.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: crossAxisCount,
                  crossAxisSpacing: AppSpacing.lg,
                  mainAxisSpacing: AppSpacing.lg,
                  mainAxisExtent: 215,
                ),
                itemBuilder: (_, idx) {
                  final r = paged[idx];
                  return RoomTileCard(
                    room: r,
                    onTap: () => context.go('/rooms/${r.id}'),
                    onView: () => context.go('/rooms/${r.id}'),
                    onEdit: () => _openRoomForm(r),
                    onDelete: () => _confirmDelete(r),
                  );
                },
              );
            },
          ),
          const SizedBox(height: AppSpacing.lg),
          AppSurfaceCard(
            padding: EdgeInsets.zero,
            child: PaginationWidget(
              currentPage: page,
              totalItems: filtered.length,
              pageSize: _pageSize,
              onPageChanged: (p) => setState(() => _page = p),
            ),
          ),
        ] else
          AppSurfaceCard(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                AppTable<RoomItem>(
                  items: paged,
                  onRowTap: (r) => context.go('/rooms/${r.id}'),
                  columns: [
                    AppTableColumn(
                      label: 'MÃ PHÒNG',
                      width: 110,
                      cellBuilder: (r) => CodeBadge(r.code),
                    ),
                    AppTableColumn(
                      label: 'TÊN PHÒNG',
                      flex: 2,
                      cellBuilder: (r) => Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(r.name, style: AppTypography.bodyBold),
                          if (r.description.isNotEmpty)
                            Text(
                              r.description,
                              style: AppTypography.caption,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                        ],
                      ),
                    ),
                    AppTableColumn(
                      label: 'TÒA NHÀ',
                      flex: 2,
                      cellBuilder: (r) => Text(
                        r.propertyName,
                        style: AppTypography.bodyMd,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    AppTableColumn(
                      label: 'GIÁ THUÊ',
                      width: 130,
                      cellBuilder: (r) => Text(
                        AppFormatters.currency(r.rentPrice),
                        style: AppTypography.bodyBold.copyWith(
                          color: AppColors.secondary,
                        ),
                      ),
                    ),
                    AppTableColumn(
                      label: 'DIỆN TÍCH',
                      width: 100,
                      cellBuilder: (r) => Text(
                        '${AppFormatters.area(r.area)} m²',
                        style: AppTypography.bodyMd,
                      ),
                    ),
                    AppTableColumn(
                      label: 'SỨC CHỨA',
                      width: 120,
                      cellBuilder: (r) => Text(
                        '${r.currentOccupants} / ${r.maxOccupants} người',
                        style: AppTypography.bodyMedium,
                      ),
                    ),
                    AppTableColumn(
                      label: 'TRẠNG THÁI',
                      width: 150,
                      cellBuilder: (r) => StatusBadge.fromRoomStatus(r.status),
                    ),
                    AppTableColumn(
                      label: 'THAO TÁC',
                      width: 130,
                      alignment: Alignment.centerRight,
                      cellBuilder: (r) => Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            tooltip: 'Xem chi tiết',
                            icon: const Icon(
                              Icons.visibility_outlined,
                              size: 18,
                              color: AppColors.textSecondary,
                            ),
                            onPressed: () => context.go('/rooms/${r.id}'),
                          ),
                          IconButton(
                            tooltip: 'Chỉnh sửa',
                            icon: const Icon(
                              Icons.edit_outlined,
                              size: 18,
                              color: AppColors.textSecondary,
                            ),
                            onPressed: () => _openRoomForm(r),
                          ),
                          IconButton(
                            tooltip: 'Xóa phòng',
                            icon: const Icon(
                              Icons.delete_outline_rounded,
                              size: 18,
                              color: AppColors.error,
                            ),
                            onPressed: () => _confirmDelete(r),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                PaginationWidget(
                  currentPage: page,
                  totalItems: filtered.length,
                  pageSize: _pageSize,
                  onPageChanged: (p) => setState(() => _page = p),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _ViewModeToggle extends StatelessWidget {
  final bool isGridView;
  final ValueChanged<bool> onChanged;

  const _ViewModeToggle({
    required this.isGridView,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(AppSpacing.buttonRadius),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ToggleChip(
            icon: Icons.table_rows_outlined,
            label: 'Bảng',
            selected: !isGridView,
            onTap: () => onChanged(false),
          ),
          _ToggleChip(
            icon: Icons.grid_view_rounded,
            label: 'Thẻ',
            selected: isGridView,
            onTap: () => onChanged(true),
          ),
        ],
      ),
    );
  }
}

class _ToggleChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _ToggleChip({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppSpacing.badgeRadius),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.labelGap,
        ),
        decoration: BoxDecoration(
          color: selected ? AppColors.surface : Colors.transparent,
          borderRadius: BorderRadius.circular(AppSpacing.badgeRadius),
          boxShadow: selected ? AppSpacing.shadowLevel1 : const [],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: selected ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              label,
              style: AppTypography.labelSm.copyWith(
                color: selected ? AppColors.primary : AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

