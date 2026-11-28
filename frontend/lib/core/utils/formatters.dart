import 'package:intl/intl.dart';

class AppFormatters {
  AppFormatters._();

  static final NumberFormat _currency = NumberFormat.decimalPattern('vi_VN');

  static String currency(num? amount) {
    return '${_currency.format(amount ?? 0)} đ';
  }

  /// Diện tích (m²): giữ phần thập phân khi có (1.5 -> "1.5"), bỏ ".0" khi là số nguyên (20.0 -> "20").
  /// Không làm tròn 1.5 thành 2.
  static String area(num? value) {
    final v = (value ?? 0).toDouble();
    return v.toStringAsFixed(2).replaceFirst(RegExp(r'\.?0+$'), '');
  }

  static String date(DateTime? dt) {
    if (dt == null) return '—';
    return DateFormat('dd/MM/yyyy').format(dt);
  }

  static String dateStr(String? raw) {
    if (raw == null || raw.isEmpty) return '—';
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    return DateFormat('dd/MM/yyyy').format(parsed.toLocal());
  }
}

