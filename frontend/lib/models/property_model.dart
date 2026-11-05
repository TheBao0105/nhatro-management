import 'room_model.dart';

class PropertyModel {
  final int id;
  final int? landlordId;
  final String? landlordName;
  final String name;
  final String address;
  final String? ward;
  final String? district;
  final String? city;
  final String? fullAddress;
  final int totalFloors;
  final double electricityRate;
  final double waterRate;
  final double internetRate;
  final String? description;
  final String? rules;
  final String? imageUrl;
  final int totalRoomsCount;
  final int availableRoomsCount;
  final int occupiedRoomsCount;
  final List<RoomModel> rooms;
  final String? createdAt;

  PropertyModel({
    required this.id,
    this.landlordId,
    this.landlordName,
    required this.name,
    required this.address,
    this.ward,
    this.district,
    this.city,
    this.fullAddress,
    this.totalFloors = 1,
    this.electricityRate = 3500.0,
    this.waterRate = 20000.0,
    this.internetRate = 100000.0,
    this.description,
    this.rules,
    this.imageUrl,
    this.totalRoomsCount = 0,
    this.availableRoomsCount = 0,
    this.occupiedRoomsCount = 0,
    this.rooms = const [],
    this.createdAt,
  });

  factory PropertyModel.fromJson(Map<String, dynamic> json) {
    List<RoomModel> roomList = [];
    if (json['rooms'] != null && json['rooms'] is List) {
      roomList = (json['rooms'] as List)
          .map((r) => RoomModel.fromJson(r))
          .toList();
    }

    return PropertyModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      landlordId: json['landlord'] is int
          ? json['landlord']
          : int.tryParse(json['landlord'].toString()),
      landlordName: json['landlord_name'],
      name: json['name'] ?? '',
      address: json['address'] ?? '',
      ward: json['ward'],
      district: json['district'],
      city: json['city'],
      fullAddress: json['full_address'] ?? json['address'],
      totalFloors: json['total_floors'] is int
          ? json['total_floors']
          : int.tryParse(json['total_floors'].toString()) ?? 1,
      electricityRate: (json['electricity_rate'] is num)
          ? (json['electricity_rate'] as num).toDouble()
          : double.tryParse(json['electricity_rate'].toString()) ?? 3500.0,
      waterRate: (json['water_rate'] is num)
          ? (json['water_rate'] as num).toDouble()
          : double.tryParse(json['water_rate'].toString()) ?? 20000.0,
      internetRate: (json['internet_rate'] is num)
          ? (json['internet_rate'] as num).toDouble()
          : double.tryParse(json['internet_rate'].toString()) ?? 100000.0,
      description: json['description'],
      rules: json['rules'],
      imageUrl: json['image_url'],
      totalRoomsCount: json['total_rooms_count'] is int
          ? json['total_rooms_count']
          : (json['rooms'] is List ? (json['rooms'] as List).length : 0),
      availableRoomsCount: json['available_rooms_count'] is int
          ? json['available_rooms_count']
          : 0,
      occupiedRoomsCount: json['occupied_rooms_count'] is int
          ? json['occupied_rooms_count']
          : 0,
      rooms: roomList,
      createdAt: json['created_at'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'address': address,
      'ward': ward,
      'district': district,
      'city': city,
      'total_floors': totalFloors,
      'electricity_rate': electricityRate,
      'water_rate': waterRate,
      'internet_rate': internetRate,
      'description': description,
      'rules': rules,
      'image_url': imageUrl,
    };
  }
}

