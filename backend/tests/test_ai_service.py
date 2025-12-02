"""
Tests for AI Service.

Tests cover:
- Singleton pattern
- Fallback content when AI is disabled
- Game name generation
- Player nickname generation
- Room description generation
- Batch room description generation
- Status reporting
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.ai_service import (
    AIService,
    FALLBACK_GAME_NAMES,
    FALLBACK_NICKNAMES,
    FALLBACK_DESCRIPTIONS,
    MONSTER_NICKNAME_TEMPLATES
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def disabled_ai_service():
    """Create an AI service with AI disabled (using fallbacks)."""
    service = object.__new__(AIService)
    service._client = None
    service._enabled = False
    service._initialized = True
    return service


@pytest.fixture
def mock_ai_response():
    """Create a mock OpenAI response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="AI Generated Content"))
    ]
    return mock_response


# ============================================================================
# SINGLETON TESTS
# ============================================================================

class TestAIServiceSingleton:
    """Tests for singleton behavior."""
    
    def test_ai_service_is_singleton(self):
        """Multiple AIService() calls should return same instance."""
        service1 = AIService()
        service2 = AIService()
        
        assert service1 is service2


# ============================================================================
# STATUS TESTS
# ============================================================================

class TestAIServiceStatus:
    """Tests for status reporting."""
    
    def test_is_enabled_when_disabled(self, disabled_ai_service):
        """is_enabled should return False when AI is disabled."""
        assert disabled_ai_service.is_enabled is False
    
    def test_get_status_when_disabled(self, disabled_ai_service):
        """get_status should report disabled state."""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.azure_openai.endpoint = None
            mock_settings.azure_openai.deployment = None
            
            status = disabled_ai_service.get_status()
            
            assert status["enabled"] is False
            assert status["fallback_available"] is True


# ============================================================================
# FALLBACK GAME NAME TESTS
# ============================================================================

class TestFallbackGameName:
    """Tests for fallback game name generation."""
    
    @pytest.mark.asyncio
    async def test_generate_game_name_uses_fallback(self, disabled_ai_service):
        """When AI disabled, should use fallback names."""
        name = await disabled_ai_service.generate_game_name()
        
        assert name in FALLBACK_GAME_NAMES
    
    @pytest.mark.asyncio
    async def test_game_names_vary(self, disabled_ai_service):
        """Should generate varied names (probabilistically)."""
        names = set()
        for _ in range(20):
            name = await disabled_ai_service.generate_game_name()
            names.add(name)
        
        # With 50 fallback names and 20 trials, very likely to get at least 5 unique
        assert len(names) > 1


# ============================================================================
# FALLBACK NICKNAME TESTS
# ============================================================================

class TestFallbackNickname:
    """Tests for fallback nickname generation."""
    
    @pytest.mark.asyncio
    async def test_generate_nickname_uses_monster_template(self, disabled_ai_service):
        """When AI disabled and kills present, should use monster template."""
        kills = {"goblin": 10, "orc": 5}
        
        nickname = await disabled_ai_service.generate_player_nickname(kills, 15)
        
        # Should be from goblin templates (top kill)
        assert nickname in MONSTER_NICKNAME_TEMPLATES["goblin"]
    
    @pytest.mark.asyncio
    async def test_generate_nickname_generic_fallback(self, disabled_ai_service):
        """When no kills or unknown type, use generic fallback."""
        nickname = await disabled_ai_service.generate_player_nickname({}, 0)
        
        assert nickname in FALLBACK_NICKNAMES
    
    @pytest.mark.asyncio
    async def test_nickname_for_unknown_monster_type(self, disabled_ai_service):
        """Unknown monster type should fall back to generic."""
        kills = {"unknown_monster": 10}
        
        nickname = await disabled_ai_service.generate_player_nickname(kills, 10)
        
        assert nickname in FALLBACK_NICKNAMES


# ============================================================================
# FALLBACK ROOM DESCRIPTION TESTS
# ============================================================================

class TestFallbackRoomDescription:
    """Tests for fallback room description generation."""
    
    @pytest.mark.asyncio
    async def test_generate_description_uses_fallback(self, disabled_ai_service):
        """When AI disabled, should use fallback descriptions."""
        description = await disabled_ai_service.generate_room_description(
            room_type="library",
            room_name="Ancient Library",
            room_width=10,
            room_height=8,
            furniture_count=2
        )
        
        assert description in FALLBACK_DESCRIPTIONS["library"]
    
    @pytest.mark.asyncio
    async def test_unknown_room_type_uses_chamber(self, disabled_ai_service):
        """Unknown room type should fall back to chamber descriptions."""
        description = await disabled_ai_service.generate_room_description(
            room_type="unknown_type",
            room_name="Mystery Room",
            room_width=10,
            room_height=10,
            furniture_count=0
        )
        
        assert description in FALLBACK_DESCRIPTIONS["chamber"]
    
    @pytest.mark.asyncio
    async def test_all_room_types_have_fallbacks(self, disabled_ai_service):
        """All defined room types should have fallback descriptions."""
        room_types = ["chamber", "library", "armory", "bedroom", "storage",
                      "throne_room", "dining_hall", "crypt", "treasury",
                      "dungeon_cell", "alchemy_lab", "guard_post"]
        
        for room_type in room_types:
            description = await disabled_ai_service.generate_room_description(
                room_type=room_type,
                room_name=f"Test {room_type}",
                room_width=10,
                room_height=10,
                furniture_count=1
            )
            
            assert description in FALLBACK_DESCRIPTIONS[room_type]


# ============================================================================
# BATCH ROOM DESCRIPTION TESTS
# ============================================================================

class TestBatchRoomDescriptions:
    """Tests for batch room description generation."""
    
    @pytest.mark.asyncio
    async def test_generate_room_descriptions_batch(self, disabled_ai_service):
        """Should generate descriptions for multiple rooms."""
        rooms = [
            {"id": "r1", "room_type": "library", "name": "Library", "width": 10, "height": 10},
            {"id": "r2", "room_type": "armory", "name": "Armory", "width": 8, "height": 8},
            {"id": "r3", "room_type": "crypt", "name": "Crypt", "width": 12, "height": 6}
        ]
        
        results = await disabled_ai_service.generate_room_descriptions(rooms)
        
        assert len(results) == 3
        for room in results:
            assert "description" in room
            assert len(room["description"]) > 0
    
    @pytest.mark.asyncio
    async def test_batch_preserves_room_data(self, disabled_ai_service):
        """Batch generation should preserve original room data."""
        rooms = [
            {
                "id": "r1",
                "room_type": "chamber",
                "name": "Test Chamber",
                "width": 10,
                "height": 10,
                "custom_field": "custom_value"
            }
        ]
        
        results = await disabled_ai_service.generate_room_descriptions(rooms)
        
        assert results[0]["id"] == "r1"
        assert results[0]["custom_field"] == "custom_value"


# ============================================================================
# AI-ENABLED TESTS (WITH MOCKING)
# ============================================================================

class TestAIEnabledGeneration:
    """Tests for when AI is enabled (using mocks)."""
    
    @pytest.fixture
    def enabled_ai_service(self, mock_ai_response):
        """Create an AI service with mocked client."""
        service = object.__new__(AIService)
        service._client = MagicMock()
        service._client.chat.completions.create = MagicMock(return_value=mock_ai_response)
        service._enabled = True
        service._initialized = True
        return service
    
    @pytest.mark.asyncio
    async def test_game_name_uses_ai_when_enabled(self, enabled_ai_service):
        """When AI enabled, should call OpenAI API."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="The Dark Depths"))]
            mock_thread.return_value = mock_response
            
            name = await enabled_ai_service.generate_game_name()
            
            mock_thread.assert_called_once()
            assert name == "The Dark Depths"
    
    @pytest.mark.asyncio
    async def test_nickname_uses_ai_when_enabled(self, enabled_ai_service):
        """When AI enabled, should call OpenAI for nickname."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="The Brave Hunter"))]
            mock_thread.return_value = mock_response
            
            kills = {"goblin": 5}
            nickname = await enabled_ai_service.generate_player_nickname(kills, 5)
            
            mock_thread.assert_called_once()
            assert nickname == "The Brave Hunter"
    
    @pytest.mark.asyncio
    async def test_nickname_adds_the_prefix(self, enabled_ai_service):
        """Nickname should start with 'The' even if AI omits it."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Brave Hunter"))]
            mock_thread.return_value = mock_response
            
            nickname = await enabled_ai_service.generate_player_nickname({"orc": 3}, 3)
            
            assert nickname.startswith("The ")
    
    @pytest.mark.asyncio
    async def test_room_description_uses_ai_when_enabled(self, enabled_ai_service):
        """When AI enabled, should call OpenAI for room description."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(
                content="You enter a magnificent library filled with ancient tomes."
            ))]
            mock_thread.return_value = mock_response
            
            description = await enabled_ai_service.generate_room_description(
                room_type="library",
                room_name="Grand Library",
                room_width=15,
                room_height=12,
                furniture_count=4
            )
            
            mock_thread.assert_called_once()
            assert "library" in description.lower()


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestAIServiceErrorHandling:
    """Tests for error handling in AI service."""
    
    @pytest.fixture
    def failing_ai_service(self):
        """Create an AI service that fails on API calls."""
        service = object.__new__(AIService)
        service._client = MagicMock()
        service._client.chat.completions.create = MagicMock(side_effect=Exception("API Error"))
        service._enabled = True
        service._initialized = True
        return service
    
    @pytest.mark.asyncio
    async def test_game_name_falls_back_on_error(self, failing_ai_service):
        """Should fall back to default names on API error."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("API Error")
            
            name = await failing_ai_service.generate_game_name()
            
            assert name in FALLBACK_GAME_NAMES
    
    @pytest.mark.asyncio
    async def test_nickname_falls_back_on_error(self, failing_ai_service):
        """Should fall back to default nicknames on API error."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("API Error")
            
            kills = {"goblin": 10}
            nickname = await failing_ai_service.generate_player_nickname(kills, 10)
            
            # Should use goblin template
            assert nickname in MONSTER_NICKNAME_TEMPLATES["goblin"]
    
    @pytest.mark.asyncio
    async def test_description_falls_back_on_error(self, failing_ai_service):
        """Should fall back to default descriptions on API error."""
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("API Error")
            
            description = await failing_ai_service.generate_room_description(
                room_type="armory",
                room_name="Weapons Room",
                room_width=10,
                room_height=10,
                furniture_count=3
            )
            
            assert description in FALLBACK_DESCRIPTIONS["armory"]


# ============================================================================
# FALLBACK CONTENT QUALITY TESTS
# ============================================================================

class TestFallbackContentQuality:
    """Tests to ensure fallback content is reasonable."""
    
    def test_fallback_game_names_are_unique(self):
        """All fallback game names should be unique."""
        assert len(FALLBACK_GAME_NAMES) == len(set(FALLBACK_GAME_NAMES))
    
    def test_fallback_game_names_not_empty(self):
        """Should have at least 20 fallback game names."""
        assert len(FALLBACK_GAME_NAMES) >= 20
    
    def test_fallback_nicknames_are_unique(self):
        """All fallback nicknames should be unique."""
        assert len(FALLBACK_NICKNAMES) == len(set(FALLBACK_NICKNAMES))
    
    def test_monster_templates_start_with_the(self):
        """Monster nickname templates should follow pattern."""
        for monster_type, templates in MONSTER_NICKNAME_TEMPLATES.items():
            for template in templates:
                # Either starts with "The" or is a title-like phrase
                assert template[0].isupper(), f"Template should be capitalized: {template}"
    
    def test_all_fallback_descriptions_non_empty(self):
        """All fallback descriptions should be non-empty."""
        for room_type, descriptions in FALLBACK_DESCRIPTIONS.items():
            assert len(descriptions) > 0, f"No descriptions for {room_type}"
            for desc in descriptions:
                assert len(desc) > 50, f"Description too short for {room_type}"
