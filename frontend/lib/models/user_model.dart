class UserModel {
  final int id;
  final String username;
  final String? email;
  final String? fullName;
  final String? firstName;
  final String? lastName;
  final String role;
  final String? roleDisplay;
  final String? phoneNumber;
  final String? identityCard;
  final String? address;
  final String? avatarUrl;

  UserModel({
    required this.id,
    required this.username,
    this.email,
    this.fullName,
    this.firstName,
    this.lastName,
    required this.role,
    this.roleDisplay,
    this.phoneNumber,
    this.identityCard,
    this.address,
    this.avatarUrl,
  });

  bool get isAdmin => role == 'ADMIN';
  bool get isLandlord => role == 'LANDLORD';
  bool get isTenant => role == 'TENANT';
  bool get isStaff => role == 'STAFF';

  String get displayName =>
      (fullName != null && fullName!.trim().isNotEmpty) ? fullName! : username;

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      username: json['username'] ?? '',
      email: json['email'],
      fullName: json['full_name'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      role: json['role'] ?? 'LANDLORD',
      roleDisplay: json['role_display'] ?? json['role'],
      phoneNumber: json['phone_number'],
      identityCard: json['identity_card'],
      address: json['address'],
      avatarUrl: json['avatar_url'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'full_name': fullName,
      'first_name': firstName,
      'last_name': lastName,
      'role': role,
      'role_display': roleDisplay,
      'phone_number': phoneNumber,
      'identity_card': identityCard,
      'address': address,
      'avatar_url': avatarUrl,
    };
  }
}

