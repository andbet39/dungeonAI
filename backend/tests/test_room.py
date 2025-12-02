"""
Tests for Room entity.

Tests cover:
- Room creation and properties
- Coordinate calculations (center, bounds)
- Point containment checking
- Serialization and deserialization
- Room info for client
"""
import pytest
from app.domain.entities import Room


class TestRoomCreation:
    """Tests for Room instantiation."""
    
    def test_create_room_with_required_fields(self):
        """Creating a room with required fields should work."""
        room = Room(id="r1", x=5, y=10, width=8, height=6)
        
        assert room.id == "r1"
        assert room.x == 5
        assert room.y == 10
        assert room.width == 8
        assert room.height == 6
    
    def test_room_defaults(self):
        """Room should have sensible defaults."""
        room = Room(id="r1", x=0, y=0, width=10, height=10)
        
        assert room.room_type == "chamber"
        assert room.name == ""
        assert room.description == ""
        assert room.furniture == []
        assert room.connected_rooms == []
        assert room.visited is False
        assert room.locked is False
        assert room.light_level == 100
    
    def test_create_room_with_all_fields(self, library_room):
        """Room with all fields set should work correctly."""
        assert library_room.room_type == "library"
        assert library_room.name == "Ancient Library"
        assert library_room.visited is True
        assert len(library_room.furniture) == 2


class TestRoomCoordinates:
    """Tests for room coordinate calculations."""
    
    def test_center_x_calculation(self, basic_room):
        """center_x should be x + width // 2."""
        # Room: x=2, width=10 -> center_x = 2 + 5 = 7
        assert basic_room.center_x == 7
    
    def test_center_y_calculation(self, basic_room):
        """center_y should be y + height // 2."""
        # Room: y=2, height=8 -> center_y = 2 + 4 = 6
        assert basic_room.center_y == 6
    
    def test_center_tuple(self, basic_room):
        """center property should return (center_x, center_y)."""
        assert basic_room.center == (7, 6)
    
    def test_area_calculation(self, basic_room):
        """area should be width * height."""
        # Room: width=10, height=8 -> area = 80
        assert basic_room.area == 80
    
    def test_bounds_tuple(self, basic_room):
        """bounds should return (x, y, width, height)."""
        assert basic_room.bounds == (2, 2, 10, 8)
    
    def test_small_room_area(self, small_room):
        """Small room should have small area."""
        # 4 x 4 = 16
        assert small_room.area == 16


class TestRoomContains:
    """Tests for point containment checking."""
    
    def test_contains_point_inside_room(self, basic_room):
        """Points inside room bounds should be contained."""
        # Room: x=2, y=2, width=10, height=8
        # Inside: (5, 5), (10, 8)
        assert basic_room.contains(5, 5) is True
        assert basic_room.contains(2, 2) is True  # top-left corner
        assert basic_room.contains(11, 9) is True  # bottom-right (exclusive boundary)
    
    def test_contains_point_outside_room(self, basic_room):
        """Points outside room bounds should not be contained."""
        # Room: x=2, y=2, width=10, height=8 -> valid range: x=[2,12), y=[2,10)
        assert basic_room.contains(0, 0) is False  # before room
        assert basic_room.contains(20, 20) is False  # after room
        assert basic_room.contains(1, 5) is False  # left of room
    
    def test_contains_boundary_points(self, basic_room):
        """Boundary should be inclusive for start, exclusive for end."""
        # Room: x=2, y=2, width=10, height=8
        # x range: [2, 12), y range: [2, 10)
        assert basic_room.contains(2, 2) is True  # inclusive start
        assert basic_room.contains(12, 10) is False  # exclusive end
        assert basic_room.contains(11, 9) is True  # just before exclusive end


class TestRoomVisited:
    """Tests for room visited tracking."""
    
    def test_room_starts_unvisited_by_default(self):
        """New rooms should be unvisited."""
        room = Room(id="r1", x=0, y=0, width=5, height=5)
        assert room.visited is False
    
    def test_room_can_be_marked_visited(self, basic_room):
        """Rooms can be marked as visited."""
        assert basic_room.visited is False
        basic_room.visited = True
        assert basic_room.visited is True


class TestRoomSerialization:
    """Tests for Room to_dict and from_dict methods."""
    
    def test_to_dict_includes_all_fields(self, library_room):
        """to_dict should include all room fields."""
        data = library_room.to_dict()
        
        assert data["id"] == "room-2"
        assert data["x"] == 15
        assert data["y"] == 2
        assert data["width"] == 12
        assert data["height"] == 10
        assert data["room_type"] == "library"
        assert data["name"] == "Ancient Library"
        assert data["description"] == "Shelves of dusty tomes line the walls"
        assert data["visited"] is True
        assert len(data["furniture"]) == 2
    
    def test_from_dict_creates_equivalent_room(self, basic_room):
        """from_dict should create an equivalent room."""
        data = basic_room.to_dict()
        restored = Room.from_dict(data)
        
        assert restored.id == basic_room.id
        assert restored.x == basic_room.x
        assert restored.y == basic_room.y
        assert restored.width == basic_room.width
        assert restored.height == basic_room.height
        assert restored.room_type == basic_room.room_type
        assert restored.visited == basic_room.visited
    
    def test_from_dict_handles_optional_fields(self):
        """from_dict should use defaults for missing optional fields."""
        minimal_data = {
            "id": "r1",
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10
        }
        room = Room.from_dict(minimal_data)
        
        assert room.room_type == "chamber"
        assert room.name == ""
        assert room.visited is False
        assert room.furniture == []
    
    def test_serialization_roundtrip_preserves_data(self, library_room):
        """Full serialization roundtrip should preserve all data."""
        data = library_room.to_dict()
        restored = Room.from_dict(data)
        
        assert restored.furniture == library_room.furniture
        assert restored.connected_rooms == library_room.connected_rooms
        assert restored.light_level == library_room.light_level


class TestRoomGetInfo:
    """Tests for get_info method (client-facing data)."""
    
    def test_get_info_returns_client_data(self, library_room):
        """get_info should return client-relevant fields."""
        info = library_room.get_info()
        
        assert info["id"] == "room-2"
        assert info["name"] == "Ancient Library"
        assert info["type"] == "library"
        assert info["description"] == "Shelves of dusty tomes line the walls"
    
    def test_get_info_excludes_internal_fields(self, basic_room):
        """get_info should not include internal implementation details."""
        info = basic_room.get_info()
        
        # These should not be in client info
        assert "x" not in info
        assert "y" not in info
        assert "width" not in info
        assert "height" not in info
        assert "furniture" not in info
        assert "visited" not in info


class TestRoomTypes:
    """Tests for different room types."""
    
    @pytest.mark.parametrize("room_type", [
        "chamber",
        "library",
        "armory",
        "bedroom",
        "storage",
        "throne_room",
        "dining_hall",
        "crypt",
        "treasury",
        "dungeon_cell",
        "alchemy_lab",
        "guard_post",
    ])
    def test_room_accepts_all_valid_types(self, room_type):
        """Room should accept all valid room types."""
        room = Room(
            id="test",
            x=0, y=0,
            width=10, height=10,
            room_type=room_type
        )
        assert room.room_type == room_type
    
    def test_room_preserves_unknown_type(self):
        """Room should preserve unknown room types (no validation)."""
        room = Room(
            id="test",
            x=0, y=0,
            width=10, height=10,
            room_type="mystery_room"
        )
        assert room.room_type == "mystery_room"
