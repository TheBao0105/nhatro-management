import 'package:flutter/foundation.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/property_model.dart';
import '../models/room_model.dart';

class PropertyProvider with ChangeNotifier {
  List<PropertyModel> _properties = [];
  PropertyModel? _selectedProperty;
  List<RoomModel> _rooms = [];
  Map<String, dynamic>? _propertyStats;

  bool _isLoading = false;
  String? _errorMessage;

  List<PropertyModel> get properties => _properties;
  PropertyModel? get selectedProperty => _selectedProperty;
  List<RoomModel> get rooms => _rooms;
  Map<String, dynamic>? get propertyStats => _propertyStats;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // 1. Fetch all properties
  Future<void> fetchProperties({String? search}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      String url = ApiConstants.properties;
      if (search != null && search.isNotEmpty) {
        url += '?search=${Uri.encodeComponent(search)}';
      }
      final response = await ApiClient.get(url);
      if (response is List) {
        _properties = response.map((item) => PropertyModel.fromJson(item)).toList();
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // 2. Fetch Property Detail
  Future<void> fetchPropertyDetail(int propertyId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await ApiClient.get('${ApiConstants.properties}$propertyId/');
      if (res is Map<String, dynamic>) {
        _selectedProperty = PropertyModel.fromJson(res);
      }
      await fetchRooms(propertyId);
      await fetchPropertyStats(propertyId);
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // 3. Fetch Rooms of Property
  Future<void> fetchRooms(int propertyId, {String? statusFilter}) async {
    try {
      String url = '${ApiConstants.properties}$propertyId/rooms/';
      if (statusFilter != null && statusFilter.isNotEmpty && statusFilter != 'ALL') {
        url += '?status=$statusFilter';
      }
      final res = await ApiClient.get(url);
      if (res is List) {
        _rooms = res.map((r) => RoomModel.fromJson(r)).toList();
        notifyListeners();
      }
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
    }
  }

  // 4. Fetch Property Stats
  Future<void> fetchPropertyStats(int propertyId) async {
    try {
      final res = await ApiClient.get('${ApiConstants.properties}$propertyId/stats/');
      if (res is Map<String, dynamic>) {
        _propertyStats = res;
        notifyListeners();
      }
    } catch (_) {}
  }

  // 5. Create Property
  Future<bool> createProperty(Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await ApiClient.post(ApiConstants.properties, data);
      final newProp = PropertyModel.fromJson(res);
      _properties.insert(0, newProp);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // 6. Update Property
  Future<bool> updateProperty(int id, Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await ApiClient.put('${ApiConstants.properties}$id/', data);
      final updated = PropertyModel.fromJson(res);
      final idx = _properties.indexWhere((p) => p.id == id);
      if (idx != -1) {
        _properties[idx] = updated;
      }
      if (_selectedProperty?.id == id) {
        _selectedProperty = updated;
      }
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // 7. Delete Property
  Future<bool> deleteProperty(int id) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await ApiClient.delete('${ApiConstants.properties}$id/');
      _properties.removeWhere((p) => p.id == id);
      if (_selectedProperty?.id == id) {
        _selectedProperty = null;
      }
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // 8. Create Room
  Future<bool> createRoom(Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await ApiClient.post(ApiConstants.rooms, data);
      final newRoom = RoomModel.fromJson(res);
      _rooms.add(newRoom);
      if (_selectedProperty != null) {
        await fetchPropertyStats(_selectedProperty!.id);
      }
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // 9. Update Room
  Future<bool> updateRoom(int id, Map<String, dynamic> data) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await ApiClient.put('${ApiConstants.rooms}$id/', data);
      final updated = RoomModel.fromJson(res);
      final idx = _rooms.indexWhere((r) => r.id == id);
      if (idx != -1) {
        _rooms[idx] = updated;
      }
      if (_selectedProperty != null) {
        await fetchPropertyStats(_selectedProperty!.id);
      }
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // 10. Update Room Status
  Future<bool> updateRoomStatus(int id, String status) async {
    try {
      final res = await ApiClient.patch(
        '${ApiConstants.rooms}$id/status/',
        {'status': status},
      );
      final updated = RoomModel.fromJson(res);
      final idx = _rooms.indexWhere((r) => r.id == id);
      if (idx != -1) {
        _rooms[idx] = updated;
      }
      if (_selectedProperty != null) {
        await fetchPropertyStats(_selectedProperty!.id);
      }
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  // 11. Delete Room
  Future<bool> deleteRoom(int id) async {
    try {
      await ApiClient.delete('${ApiConstants.rooms}$id/');
      _rooms.removeWhere((r) => r.id == id);
      if (_selectedProperty != null) {
        await fetchPropertyStats(_selectedProperty!.id);
      }
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      notifyListeners();
      return false;
    }
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}

