import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../theme/app_typography.dart';

class AppTextField extends StatelessWidget {
  final String label;
  final String? hint;
  final TextEditingController controller;
  final bool requiredField;
  final bool isNumber;
  final int maxLines;
  final String? Function(String?)? validator;

  /// Ẩn ký tự nhập (mật khẩu).
  final bool obscureText;

  const AppTextField({
    super.key,
    required this.label,
    required this.controller,
    this.hint,
    this.requiredField = false,
    this.isNumber = false,
    this.maxLines = 1,
    this.validator,
    this.obscureText = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Flexible(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
                style: AppTypography.captionMedium.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            if (requiredField)
              Text(
                ' *',
                style: AppTypography.captionMedium.copyWith(color: AppColors.error),
              ),
          ],
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller: controller,
          maxLines: obscureText ? 1 : maxLines,
          obscureText: obscureText,
          style: AppTypography.body,
          keyboardType: isNumber
              ? const TextInputType.numberWithOptions(decimal: true, signed: true)
              : TextInputType.text,
          decoration: InputDecoration(hintText: hint),
          validator: validator ??
              (value) {
                final v = value?.trim() ?? '';
                if (requiredField && v.isEmpty) {
                  return 'Vui lòng nhập $label';
                }
                if (isNumber && v.isNotEmpty && num.tryParse(v) == null) {
                  return '$label phải là số hợp lệ';
                }
                return null;
              },
        ),
      ],
    );
  }
}

