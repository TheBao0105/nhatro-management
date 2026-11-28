import 'package:flutter/material.dart';
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
import 'widgets/property_header_card.dart';

class PropertyPage extends StatefulWidget {
  const PropertyPage({super.key});

  @override
  State<PropertyPage> createState() => _PropertyPageState();
}

class _PropertyPageState extends State<PropertyPage> {
  final _searchCtrl = TextEditingController();
  String _statusFilter = 'ALL';
  int _page = 1;
  static const int _pageSize = 6;

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  void _openPropertyForm([PropertyItem? existing]) {
    final formKey = GlobalKey<FormState>();
    // Mã để trống khi thêm mới: Property Service tự sinh mã duy nhất (không tự đoán mã ở client).
    final codeCtrl = TextEditingController(text: existing?.code ?? '');
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final addressCtrl = TextEditingController(text: existing?.address ?? '');
    final districtCtrl = TextEditingController(text: existing?.district ?? '');
    final descCtrl = TextEditingController(text: existing?.description ?? '');
    String status = existing?.status ?? 'ACTIVE';
    bool saving = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => AlertDialog(
          title: Text(
            existing == null ? 'Thêm nhà trọ mới' : 'Chỉnh sửa nhà trọ',
            style: AppTypography.sectionTitle,
          ),
          content: SizedBox(
            width: 520,
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
                            label: 'Mã nhà trọ',
                            controller: codeCtrl,
                            hint: existing == null ? 'Để trống để hệ thống tự sinh' : null,
                            requiredField: existing != null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: AppSelect<String>(
                            label: 'Trạng thái',
                            width: null,
                            value: status,
                            options: const [
                              AppSelectOption(value: 'ACTIVE', label: 'Đang hoạt động'),
                              AppSelectOption(value: 'INACTIVE', label: 'Tạm ngưng'),
                            ],
                            onChanged: (v) => setModalState(() => status = v ?? 'ACTIVE'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    AppTextField(
                      label: 'Tên nhà trọ',
                      controller: nameCtrl,
                      hint: 'VD: Khu nhà trọ Bình Thạnh Rivera',
                      requiredField: true,
                    ),
                    const SizedBox(height: 14),
                    AppTextField(
                      label: 'Địa chỉ chi tiết',
                      controller: addressCtrl,
                      hint: 'Số nhà, tên đường (không nhập phường / quận / thành phố)',
                      requiredField: true,
                    ),
                    const SizedBox(height: 14),
                    // "Tổng số phòng" do Property Service tự tính từ các phòng thật (trường chỉ đọc),
                    // nên không có ô nhập ở đây: trước đây ô này nhận số nhưng không được lưu.
                    AppTextField(
                      label: 'Quận / Huyện / Khu vực',
                      controller: districtCtrl,
                      requiredField: true,
                    ),
                    const SizedBox(height: 14),
                    AppTextField(
                      label: 'Mô tả & tiện ích chung',
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
              label: existing == null ? 'Thêm nhà trọ' : 'Lưu thay đổi',
              isLoading: saving,
              onPressed: saving
                  ? null
                  : () async {
                if (!formKey.currentState!.validate()) return;
                final repo = context.read<AppDataRepository>();
                setModalState(() => saving = true);

                if (existing == null) {
                  // id / số phòng chỉ là giá trị tạm của model: payload gửi backend không chứa chúng,
                  // danh sách hiển thị lại dữ liệu do backend trả về sau khi đồng bộ.
                  final err = await repo.addProperty(
                    PropertyItem(
                      id: 0,
                      code: codeCtrl.text.trim(),
                      name: nameCtrl.text.trim(),
                      address: addressCtrl.text.trim(),
                      district: districtCtrl.text.trim(),
                      totalRooms: 0,
                      occupiedRooms: 0,
                      availableRooms: 0,
                      status: status,
                      description: descCtrl.text.trim(),
                    ),
                  );
                  if (!ctx.mounted || !mounted) return;
                  if (err != null) {
                    setModalState(() => saving = false);
                    showErrorToast(context, err);
                    return;
                  }
                  Navigator.pop(ctx);
                  showSuccessToast(context, 'Đã thêm nhà trọ "${nameCtrl.text.trim()}"');
                } else {
                  final err = await repo.updateProperty(
                    existing.copyWith(
                      code: codeCtrl.text.trim(),
                      name: nameCtrl.text.trim(),
                      address: addressCtrl.text.trim(),
                      district: districtCtrl.text.trim(),
                      status: status,
                      description: descCtrl.text.trim(),
                    ),
                  );
                  if (!ctx.mounted || !mounted) return;
                  if (err != null) {
                    setModalState(() => saving = false);
                    showErrorToast(context, err);
                    return;
                  }
                  Navigator.pop(ctx);
                  showSuccessToast(context, 'Đã cập nhật nhà trọ "${nameCtrl.text.trim()}"');
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showPropertyDetails(PropertyItem item) {
    final repo = context.read<AppDataRepository>();
    final rooms = repo.rooms.where((r) => r.propertyId == item.id).toList();
    final roomState = repo.sectionState(DataSection.rooms);
    // Chỉ nói "chưa có phòng" khi danh sách phòng đã tải thành công.
    final String emptyRoomsText;
    if (roomState.isForbidden) {
      emptyRoomsText = 'Tài khoản của bạn không có quyền xem danh sách phòng.';
    } else if (roomState.isError) {
      emptyRoomsText = 'Không tải được danh sách phòng: ${roomState.message ?? 'lỗi không xác định'}';
    } else if (roomState.isLoading || (repo.isSyncing && !roomState.isLoaded)) {
      emptyRoomsText = 'Đang tải danh sách phòng...';
    } else if (!roomState.isLoaded) {
      emptyRoomsText = 'Chưa tải được danh sách phòng.';
    } else {
      emptyRoomsText = 'Chưa có phòng nào được gán.';
    }

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            CodeBadge(item.code),
            const SizedBox(width: 10),
            Expanded(child: Text(item.name, style: AppTypography.sectionTitle)),
            StatusBadge.fromPropertyStatus(item.status),
          ],
        ),
        content: SizedBox(
          width: 600,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Địa chỉ: ${item.displayAddress}', style: AppTypography.body),
              const SizedBox(height: 6),
              Text('Khu vực: ${item.district}', style: AppTypography.caption),
              if (item.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text('Mô tả: ${item.description}', style: AppTypography.body),
              ],
              const Divider(height: 24),
              Row(
                children: [
                  _MiniStat(label: 'Tổng số phòng', value: '${item.totalRooms}'),
                  const SizedBox(width: 24),
                  _MiniStat(label: 'Đang thuê', value: '${item.occupiedRooms}'),
                  const SizedBox(width: 24),
                  _MiniStat(label: 'Còn trống', value: '${item.availableRooms}'),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                'Danh sách phòng thuộc nhà trọ (${rooms.length})',
                style: AppTypography.cardTitle,
              ),
              const SizedBox(height: 8),
              if (rooms.isEmpty)
                Text(emptyRoomsText, style: AppTypography.caption)
              else
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 220),
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: rooms.length,
                    separatorBuilder: (_, _) => const Divider(height: 1),
                    itemBuilder: (_, idx) {
                      final r = rooms[idx];
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Row(
                          children: [
                            CodeBadge(r.code),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                '${r.name} · ${AppFormatters.area(r.area)} m²',
                                style: AppTypography.bodyMedium,
                              ),
                            ),
                            StatusBadge.fromRoomStatus(r.status),
                          ],
                        ),
                      );
                    },
                  ),
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
  }

  Future<void> _confirmDelete(PropertyItem item) async {
    final confirmed = await ConfirmDialog.show(
      context,
      title: 'Xác nhận xóa nhà trọ',
      message:
          'Bạn có chắc chắn muốn xóa nhà trọ "${item.name}" (${item.code})? Hành động này sẽ ngừng kích hoạt dữ liệu nhà trọ.',
    );
    if (!confirmed || !mounted) return;
    final err = await context.read<AppDataRepository>().deleteProperty(item.id);
    if (!mounted) return;
    if (err != null) {
      showErrorToast(context, err);
      return;
    }
    showSuccessToast(context, 'Đã xóa nhà trọ "${item.name}"');
  }

  Future<void> _togglePropertyStatus(PropertyItem item) async {
    final nextStatus = item.status == 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    final err = await context
        .read<AppDataRepository>()
        .updatePropertyStatus(item.id, nextStatus);
    if (!mounted) return;
    if (err != null) {
      showErrorToast(context, err);
      return;
    }
    showSuccessToast(
      context,
      nextStatus == 'ACTIVE'
          ? 'Đã kích hoạt "${item.name}"'
          : 'Đã tạm ngưng "${item.name}"',
    );
  }

  @override
  Widget build(BuildContext context) {
    final repo = context.watch<AppDataRepository>();
    final query = _searchCtrl.text.trim().toLowerCase();

    final filtered = repo.properties.where((p) {
      final matchesStatus = _statusFilter == 'ALL' || p.status == _statusFilter;
      final matchesQuery = query.isEmpty ||
          p.name.toLowerCase().contains(query) ||
          p.code.toLowerCase().contains(query) ||
          p.displayAddress.toLowerCase().contains(query) ||
          p.district.toLowerCase().contains(query);
      return matchesStatus && matchesQuery;
    }).toList();

    // Sau khi xóa / lọc, số trang có thể giảm: không để trang hiện tại vượt quá trang cuối.
    final pageCount = filtered.isEmpty ? 1 : (filtered.length + _pageSize - 1) ~/ _pageSize;
    final page = _page.clamp(1, pageCount);
    final start = ((page - 1) * _pageSize).clamp(0, filtered.length);
    final end = (page * _pageSize).clamp(0, filtered.length);
    final paged = filtered.sublist(start, end);

    final activeCount =
        repo.properties.where((p) => p.status == 'ACTIVE').length;

    // Trạng thái tải riêng của từng nhóm dữ liệu (Property Service có thể lỗi khi Gateway vẫn chạy).
    final propState = repo.sectionState(DataSection.properties);
    final roomState = repo.sectionState(DataSection.rooms);
    final hasFilter = query.isNotEmpty || _statusFilter != 'ALL';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          title: 'Quản lý Tòa nhà',
          subtitle: 'Quản lý danh sách các cơ sở, tòa nhà trọ và công suất phòng.',
          actions: [
            AppButton(
              label: '+ Thêm tòa nhà mới',
              onPressed: () => _openPropertyForm(),
            ),
          ],
        ),

        // Stitch Property Header Card (Banner + Recessed Stats Strip)
        PropertyHeaderCard(
          totalProperties: repo.totalPropertiesCount,
          activeProperties: activeCount,
          totalRooms: repo.totalRoomsCount,
          occupiedRooms: repo.occupiedRoomsCount,
          availableRooms: repo.availableRoomsCount,
          maintenanceRooms: repo.maintenanceRoomsCount,
          // Chưa tải được thì hiện "—", không hiện 0 như số thật.
          propertyStatsAvailable: propState.isLoaded || repo.properties.isNotEmpty,
          roomStatsAvailable: roomState.isLoaded || repo.rooms.isNotEmpty,
        ),

        const SizedBox(height: AppSpacing.xl),

        // Filter Bar
        AppSurfaceCard(
          padding: AppSpacing.cardPadding,
          child: Wrap(
            spacing: AppSpacing.md,
            runSpacing: AppSpacing.md,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              AppSearchBar(
                controller: _searchCtrl,
                hintText: 'Tìm theo tên tòa nhà, mã, địa chỉ...',
                onChanged: (_) => setState(() => _page = 1),
              ),
              AppSelect<String>(
                label: 'Trạng thái',
                value: _statusFilter,
                options: const [
                  AppSelectOption(value: 'ALL', label: 'Tất cả trạng thái'),
                  AppSelectOption(value: 'ACTIVE', label: 'Đang hoạt động'),
                  AppSelectOption(value: 'INACTIVE', label: 'Tạm ngưng'),
                ],
                onChanged: (v) => setState(() {
                  _statusFilter = v ?? 'ALL';
                  _page = 1;
                }),
              ),
              if (query.isNotEmpty || _statusFilter != 'ALL')
                AppButton(
                  label: 'Đặt lại',
                  variant: AppButtonVariant.outlined,
                  compact: true,
                  onPressed: () => setState(() {
                    _searchCtrl.clear();
                    _statusFilter = 'ALL';
                    _page = 1;
                  }),
                ),
            ],
          ),
        ),

        const SizedBox(height: AppSpacing.lg),

        if (repo.properties.isNotEmpty && propState.isError)
          StaleDataBanner(
            key: const Key('property_list_stale'),
            message: 'Không cập nhật được danh sách tòa nhà: ${propState.message ?? 'lỗi không xác định'}. '
                'Đang hiển thị dữ liệu của lần tải trước.',
            onRetry: repo.syncWithBackend,
          ),
        if (repo.properties.isEmpty && propState.isForbidden)
          const EmptyState(
            key: Key('property_list_forbidden'),
            icon: Icons.lock_outline_rounded,
            title: 'Không có quyền xem danh sách tòa nhà',
            subtitle: 'Tài khoản của bạn không được cấp quyền truy cập dữ liệu này.',
          )
        else if (repo.properties.isEmpty && propState.isError)
          ErrorState(
            key: const Key('property_list_error'),
            message: 'Không tải được danh sách tòa nhà: ${propState.message ?? 'lỗi không xác định'}',
            onRetry: repo.syncWithBackend,
          )
        else if (repo.properties.isEmpty && (propState.isLoading || (repo.isSyncing && !propState.isLoaded)))
          const LoadingState(
            key: Key('property_list_loading'),
            message: 'Đang tải danh sách tòa nhà...',
          )
        else if (repo.properties.isEmpty && !propState.isLoaded)
          // Chưa tải và không có lượt tải nào đang chạy: không giả vờ "đang tải", không nói "rỗng".
          ErrorState(
            key: const Key('property_list_not_loaded'),
            message: repo.lastSyncError ?? 'Chưa tải được danh sách tòa nhà.',
            onRetry: repo.syncWithBackend,
          )
        else if (repo.properties.isEmpty)
          EmptyState(
            key: const Key('property_list_empty'),
            icon: Icons.apartment_rounded,
            title: 'Chưa có tòa nhà nào',
            subtitle: 'Hệ thống chưa có tòa nhà nào trong phạm vi quản lý của bạn.',
            actionLabel: '+ Thêm tòa nhà mới',
            onAction: () => _openPropertyForm(),
          )
        else if (filtered.isEmpty)
          EmptyState(
            key: const Key('property_list_no_match'),
            icon: Icons.search_off_rounded,
            title: 'Không tìm thấy tòa nhà phù hợp',
            subtitle: 'Không có tòa nhà nào khớp với từ khóa hoặc bộ lọc hiện tại.',
            actionLabel: hasFilter ? 'Đặt lại bộ lọc' : null,
            onAction: hasFilter
                ? () => setState(() {
                      _searchCtrl.clear();
                      _statusFilter = 'ALL';
                      _page = 1;
                    })
                : null,
          )
        else
          AppSurfaceCard(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                AppTable<PropertyItem>(
                  items: paged,
                  onRowTap: _showPropertyDetails,
                  columns: [
                    AppTableColumn(
                      label: 'TÒA NHÀ & THÔNG SỐ',
                      flex: 3,
                      cellBuilder: (item) => Row(
                        children: [
                          CodeBadge(item.code),
                          const SizedBox(width: AppSpacing.md),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  item.name,
                                  style: AppTypography.bodyBold,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                Text(
                                  '${item.totalRooms} phòng · ${item.district}',
                                  style: AppTypography.caption,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    AppTableColumn(
                      label: 'ĐỊA CHỈ',
                      flex: 3,
                      cellBuilder: (item) => Text(
                        item.displayAddress,
                        style: AppTypography.bodyMd,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    AppTableColumn(
                      label: 'HIỆN TRẠNG CÔNG SUẤT',
                      flex: 2,
                      cellBuilder: (item) {
                        final ratio = item.totalRooms > 0
                            ? item.occupiedRooms / item.totalRooms
                            : 0.0;
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Flexible(
                                  child: Text(
                                    '${item.occupiedRooms}/${item.totalRooms} thuê',
                                    overflow: TextOverflow.ellipsis,
                                    style: AppTypography.labelSm.copyWith(
                                      color: AppColors.primary,
                                    ),
                                  ),
                                ),
                                Flexible(
                                  child: Text(
                                    '${item.availableRooms} trống',
                                    overflow: TextOverflow.ellipsis,
                                    style: AppTypography.labelSm.copyWith(
                                      color: AppColors.successText,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpacing.xs),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(
                                AppSpacing.pillRadius,
                              ),
                              child: LinearProgressIndicator(
                                value: ratio.clamp(0.0, 1.0),
                                minHeight: 6,
                                backgroundColor: AppColors.surfaceMuted,
                                valueColor: const AlwaysStoppedAnimation<Color>(
                                  AppColors.secondary,
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                    AppTableColumn(
                      label: 'TRẠNG THÁI',
                      width: 155,
                      cellBuilder: (item) =>
                          StatusBadge.fromPropertyStatus(item.status),
                    ),
                    AppTableColumn(
                      label: 'THAO TÁC',
                      width: 165,
                      alignment: Alignment.centerRight,
                      cellBuilder: (item) => Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            tooltip: item.status == 'ACTIVE'
                                ? 'Tạm ngưng hoạt động'
                                : 'Kích hoạt lại',
                            icon: Icon(
                              item.status == 'ACTIVE'
                                  ? Icons.pause_circle_outline_rounded
                                  : Icons.play_circle_outline_rounded,
                              size: 18,
                              color: item.status == 'ACTIVE'
                                  ? AppColors.warningText
                                  : AppColors.successText,
                            ),
                            onPressed: () => _togglePropertyStatus(item),
                          ),
                          IconButton(
                            tooltip: 'Xem chi tiết',
                            icon: const Icon(
                              Icons.visibility_outlined,
                              size: 18,
                              color: AppColors.textSecondary,
                            ),
                            onPressed: () => _showPropertyDetails(item),
                          ),
                          IconButton(
                            tooltip: 'Chỉnh sửa',
                            icon: const Icon(
                              Icons.edit_outlined,
                              size: 18,
                              color: AppColors.textSecondary,
                            ),
                            onPressed: () => _openPropertyForm(item),
                          ),
                          IconButton(
                            tooltip: 'Xóa',
                            icon: const Icon(
                              Icons.delete_outline_rounded,
                              size: 18,
                              color: AppColors.error,
                            ),
                            onPressed: () => _confirmDelete(item),
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

class _MiniStat extends StatelessWidget {
  final String label;
  final String value;
  const _MiniStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTypography.caption),
        const SizedBox(height: 2),
        Text(value, style: AppTypography.sectionTitle),
      ],
    );
  }
}

