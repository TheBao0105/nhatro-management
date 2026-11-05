class RoomModel {
  final int id;
  final int propertyId;
  final String? propertyName;
  final String roomNumber;
  final int floor;
  final double area;
  final double rentPrice;
  final double depositAmount;
  final int maxOccupants;
  final String status;
  final String? statusDisplay;
  final String? amenities;
  final String? description;
  final double initialElectricReading;
  final double initialWaterReading;
  final String? createdAt;

  RoomModel({
    required this.id,
    required this.propertyId,
    this.propertyName,
    required this.roomNumber,
    required this.floor,
    required this.area,
    required this.rentPrice,
    required this.depositAmount,
    required this.maxOccupants,
    required this.status,
    this.statusDisplay,
    this.amenities,
    this.description,
    this.initialElectricReading = 0.0,
    this.initialWaterReading = 0.0,
    this.createdAt,
  });

  bool get isAvailable => status == 'AVAILABLE';
  bool get isOccupied => status == 'OCCUPIED';
  bool get isMaintenance => status == 'MAINTENANCE';
  bool get isReserved => status == 'RESERVED';

  factory RoomModel.fromJson(Map<String, dynamic> json) {
    return RoomModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      propertyId: json['property'] is int
          ? json['property']
          : int.tryParse(json['property'].toString()) ?? 0,
      propertyName: json['property_name'],
      roomNumber: json['room_number'] ?? '',
      floor: json['floor'] is int ? json['floor'] : int.tryParse(json['floor'].toString()) ?? 1,
      area: (json['area'] is num) ? (json['area'] as num).toDouble() : 20.0,
      rentPrice: (json['rent_price'] is num)
          ? (json['rent_price'] as num).toDouble()
          : double.tryParse(json['rent_price'].toString()) ?? 0.0,
      depositAmount: (json['deposit_amount'] is num)
          ? (json['deposit_amount'] as num).toDouble()
          : double.tryParse(json['deposit_amount']?.toString() ?? '') ?? 0.0,
      maxOccupants: json['max_occupants'] is int
          ? json['max_occupants']
          : int.tryParse(json['max_occupants'].toString()) ?? 2,
      status: json['status'] ?? 'AVAILABLE',
      statusDisplay: json['status_display'] ?? 'Còn trống',
      amenities: json['amenities'],
      description: json['description'],
      initialElectricReading: (json['initial_electric_reading'] is num)
          ? (json['initial_electric_reading'] as num).toDouble()
          : 0.0,
      initialWaterReading: (json['initial_water_reading'] is num)
          ? (json['initial_water_reading'] as num).toDouble()
          : 0.0,
      createdAt: json['created_at'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'property': propertyId,
      'room_number': roomNumber,
      'floor': floor,
      'area': area,
      'rent_price': rentPrice,
      'deposit_amount': depositAmount,
      'max_occupants': maxOccupants,
      'status': status,
      'amenities': amenities,
      'description': description,
      'initial_electric_reading': initialElectricReading,
      'initial_water_reading': initialWaterReading,
    };
  }
}
