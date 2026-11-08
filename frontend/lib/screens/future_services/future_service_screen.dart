import 'package:flutter/material.dart';
import '../../core/network/api_client.dart';

class FutureServiceScreen extends StatefulWidget {
  final String title;
  final String serviceName;
  final String sprintName;
  final IconData icon;
  final Color themeColor;
  final String statusApiUrl;
  final List<String> plannedFeatures;

  const FutureServiceScreen({
    super.key,
    required this.title,
    required this.serviceName,
    required this.sprintName,
    required this.icon,
    required this.themeColor,
    required this.statusApiUrl,
    required this.plannedFeatures,
  });

  @override
  State<FutureServiceScreen> createState() => _FutureServiceScreenState();
}

class _FutureServiceScreenState extends State<FutureServiceScreen> {
  bool _isLoading = false;
  Map<String, dynamic>? _backendStatus;
  String? _error;

  @override
  void initState() {
    super.initState();
    _checkBackendServiceStatus();
  }

  Future<void> _checkBackendServiceStatus() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await ApiClient.get(widget.statusApiUrl);
      if (res is Map<String, dynamic>) {
        setState(() {
          _backendStatus = res;
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(widget.title, style: const TextStyle(fontWeight: FontWeight.w700)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Hero Banner
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      widget.themeColor,
                      widget.themeColor.withOpacity(0.85),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(22),
                  boxShadow: [
                    BoxShadow(
                      color: widget.themeColor.withOpacity(0.25),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(widget.icon, size: 40, color: Colors.white),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      widget.serviceName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.3,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.25),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        widget.sprintName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Backend Health & SOA Database Status Card
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Kết nối Microservice Backend',
                          style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                        ),
                        IconButton(
                          icon: const Icon(Icons.refresh_rounded, size: 20, color: Color(0xFF64748B)),
                          onPressed: _checkBackendServiceStatus,
                          tooltip: 'Kiểm tra lại',
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    if (_isLoading)
                      const Center(
                        child: Padding(
                          padding: EdgeInsets.all(12.0),
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    else if (_backendStatus != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF0FDF4),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFBBF7D0)),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check_circle_rounded, color: Color(0xFF16A34A), size: 22),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Dịch vụ đã sẵn sàng trong cấu trúc SOA: ${_backendStatus!['status']}',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFF15803D),
                                      fontSize: 13,
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    'Database riêng: ${_backendStatus!['database'] ?? 'Isolated DB'}',
                                    style: const TextStyle(color: Color(0xFF166534), fontSize: 12, fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${_backendStatus!['message'] ?? 'Hoàn thành trong sprint tiếp theo.'}',
                                    style: const TextStyle(color: Color(0xFF4B5563), fontSize: 12),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      )
                    else
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFEF2F2),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFFECACA)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.info_outline_rounded, color: Color(0xFFDC2626), size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _error ?? 'Không thể kết nối đến máy chủ backend.',
                                style: const TextStyle(color: Color(0xFFDC2626), fontSize: 12.5),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),

              const SizedBox(height: 18),

              // Roadmap Planned Features
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.checklist_rounded, size: 20, color: Color(0xFF2563EB)),
                        SizedBox(width: 8),
                        Text(
                          'Các tính năng sẽ hoàn thành trong Sprint tiếp theo:',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    ...widget.plannedFeatures.map((feat) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                margin: const EdgeInsets.only(top: 2),
                                padding: const EdgeInsets.all(3),
                                decoration: BoxDecoration(
                                  color: widget.themeColor.withOpacity(0.12),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(Icons.arrow_forward_rounded, size: 12, color: widget.themeColor),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  feat,
                                  style: const TextStyle(
                                    fontSize: 13.5,
                                    color: Color(0xFF334155),
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
