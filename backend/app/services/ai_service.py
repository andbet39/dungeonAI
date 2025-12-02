"""
AI service for generating room descriptions using Azure OpenAI.
Generates atmospheric, immersive descriptions for dungeon rooms.
"""
import asyncio
import random
from typing import Optional

from ..config import settings


# Fallback game names for when Azure OpenAI is not available
FALLBACK_GAME_NAMES = [
    "The Sunken Crypt", "Halls of the Forgotten", "Shadowmere Depths",
    "The Obsidian Labyrinth", "Caverns of Despair", "The Iron Tombs",
    "Whisperwind Dungeon", "The Crimson Vault", "Abyssal Corridors",
    "The Shattered Keep", "Dungeons of Dread", "The Frozen Crypts",
    "Serpent's Hollow", "The Cursed Mines", "Blackstone Prison",
    "The Haunted Galleries", "Netherworld Passages", "The Lost Catacombs",
    "Dragonfire Depths", "The Rusted Gates", "Stormhaven Dungeon",
    "The Withered Halls", "Moonshade Caverns", "The Silent Tombs",
    "Darkwater Depths", "The Crumbling Fortress", "Venomfang Lair",
    "The Forgotten Temple", "Ashfall Dungeon", "The Bone Pits",
    "Shadowkeep Ruins", "The Emerald Depths", "Frostbite Caverns",
    "The Wailing Mines", "Thornwood Dungeon", "The Ancient Vault",
    "Grimstone Keep", "The Spectral Halls", "Bloodmoon Crypt",
    "The Twisted Passages", "Doomfire Depths", "The Starless Abyss",
    "Wraithwood Dungeon", "The Gilded Prison", "Nightfall Caverns",
    "The Screaming Halls", "Ironhold Depths", "The Petrified Forest",
    "Soulreaver Dungeon", "The Endless Maze"
]


# Fallback nicknames for players when Azure OpenAI is not available
FALLBACK_NICKNAMES = [
    "The Monster Slayer", "The Dungeon Champion", "The Fearless",
    "The Bane of Beasts", "The Undaunted", "The Relentless",
    "The Shadow Walker", "The Brave", "The Victorious",
    "The Unyielding", "The Legendary", "The Mighty",
    "The Vanquisher", "The Conqueror", "The Invincible",
    "The Terror of Dungeons", "The Beast Hunter", "The Goblin Bane",
    "The Orc Slayer", "The Skeleton Crusher", "The Undead Scourge",
    "The Spider Squasher", "The Ghost Whisperer", "The Rat King",
    "The Cultist Hunter", "The Mimic Finder", "The Slime Destroyer"
]


# Monster type specific nickname templates
MONSTER_NICKNAME_TEMPLATES = {
    "goblin": ["The Goblin Slayer", "Bane of Goblinkind", "The Green Menace's End"],
    "orc": ["The Orc Crusher", "Scourge of Orcs", "The Tusked Terror's Bane"],
    "skeleton": ["The Bone Breaker", "Scourge of the Undead", "The Skeleton Smasher"],
    "zombie": ["The Zombie Hunter", "Slayer of the Risen", "The Undead's End"],
    "ghost": ["The Ghost Hunter", "The Spirit Banisher", "The Spectral Slayer"],
    "giant_spider": ["The Spider Slayer", "Arachnid's Bane", "The Web Cutter"],
    "kobold": ["The Kobold Crusher", "Terror of Kobolds", "The Scaled Scourge"],
    "rat_swarm": ["The Rat King", "The Vermin Vanquisher", "The Plague Stopper"],
    "dark_cultist": ["The Cultist Hunter", "The Heretic Slayer", "Bane of Dark Cults"],
    "mimic": ["The Mimic Finder", "The Treasure True", "The Chest Checker"],
    "slime": ["The Slime Destroyer", "The Ooze Obliterator", "The Gelatinous Nemesis"],
    "bandit": ["The Bandit Hunter", "Scourge of Thieves", "The Outlaw's End"],
}


# Fallback descriptions for when Azure OpenAI is not available
FALLBACK_DESCRIPTIONS = {
    "chamber": [
        "A dusty chamber with ancient stone walls. Cobwebs hang from the corners, and the air smells of age and forgotten secrets.",
        "The chamber is cold and damp. Water drips somewhere in the darkness, echoing off the stone walls.",
        "An empty chamber lit only by the faint glow seeping through cracks in the ceiling. Dust motes dance in the dim light."
    ],
    "library": [
        "Towering bookshelves line the walls, though most books have crumbled to dust. A few tomes remain, their leather covers worn but intact.",
        "The library is silent save for the rustling of ancient pages. Knowledge of ages past lies scattered across dusty tables.",
        "Faded manuscripts and scrolls litter the floor. The scent of old parchment fills the air."
    ],
    "armory": [
        "Weapons racks line the walls, though most are empty. A few rusted swords and dented shields remain as reminders of past battles.",
        "The armory has been thoroughly looted. Only broken weapon handles and shattered armor pieces remain.",
        "Dust-covered weapon stands hold ancient armaments. The metal has long since lost its shine."
    ],
    "bedroom": [
        "A decrepit bed frame stands against the wall, its mattress long rotted away. Personal belongings lie scattered across the floor.",
        "The bedroom's furnishings have decayed, but traces of its former occupant remain: a faded portrait, a broken mirror.",
        "Moth-eaten curtains hang by the bed. The room feels strangely personal despite its abandonment."
    ],
    "storage": [
        "Broken crates and empty barrels fill this storage room. Whatever was kept here was taken long ago.",
        "The storage room smells of mold and decay. Rotted sacks spill their contents across the floor.",
        "Shelves sag under the weight of forgotten supplies. Most have spoiled beyond recognition."
    ],
    "throne_room": [
        "A grand throne sits upon a raised dais, its gold plating tarnished and gems pried from their settings. The room still holds an air of faded majesty.",
        "The throne room's former splendor is evident in the crumbling murals and shattered chandeliers. Power once resided here.",
        "Dust covers the throne like a burial shroud. The room echoes with the ghosts of courtly proceedings."
    ],
    "dining_hall": [
        "A long table dominates the hall, still set with tarnished plates and goblets. The feast was abandoned mid-meal, it seems.",
        "The dining hall's grandeur has faded. Rotted tapestries hang from the walls, depicting feasts and celebrations.",
        "Overturned chairs and scattered utensils suggest the diners left in haste. The table still bears the stains of ancient meals."
    ],
    "crypt": [
        "Stone sarcophagi line the walls of this crypt. The air is thick with the scent of decay and ancient burial spices.",
        "The crypt is silent as the grave. Carved names on the tombs have worn away to illegibility.",
        "Bones peek from disturbed graves. Something has been here before you, disturbing the eternal rest of the dead."
    ],
    "treasury": [
        "The treasury has been picked clean. Empty chests and scattered coins suggest vast wealth once stored here.",
        "A few gold coins glint in the darkness—overlooked perhaps, or bait for the unwary. The treasury's true riches are long gone.",
        "Broken locks and empty strongboxes tell the tale of thorough looting. Yet the room may still hold secrets."
    ],
    "dungeon_cell": [
        "Rusted chains hang from the walls of this cramped cell. The stone floor is worn smooth by generations of prisoners.",
        "The cell reeks of despair. Scratched marks on the walls count days that stretched into eternity for someone.",
        "A tiny barred window lets in a sliver of light. The cell has held many, and freed few."
    ],
    "alchemy_lab": [
        "Shattered beakers and stained workbenches fill this laboratory. Strange residues coat every surface.",
        "The alchemy lab still holds the acrid smell of experiments gone wrong. Bubbling residue drips from overturned vessels.",
        "Arcane symbols cover the walls and floor. Whatever experiments were conducted here touched upon forbidden knowledge."
    ],
    "guard_post": [
        "Weapon racks and a simple cot mark this as a guard post. The guards are long gone, but their vigilance lingers in the room's layout.",
        "The guard post offers a clear view of approaching corridors. Someone once stood watch here for dangers that eventually came.",
        "A duty roster hangs on the wall, names faded beyond reading. The guards who served here have passed into history."
    ]
}


class AIService:
    """Service for AI-powered content generation."""
    
    _instance: Optional["AIService"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "AIService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._client = None
        self._enabled = False
        self._initialize_client()
        self._initialized = True
    
    def _initialize_client(self) -> None:
        """Initialize Azure OpenAI client if configured."""
        if not settings.azure_openai.is_enabled:
            print("[AIService] Azure OpenAI not configured, using fallback descriptions")
            return
        
        try:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=settings.azure_openai.api_key,
                api_version=settings.azure_openai.api_version,
                azure_endpoint=settings.azure_openai.endpoint
            )
            self._enabled = True
            print("[AIService] Azure OpenAI client initialized successfully")
        except Exception as e:
            print(f"[AIService] Failed to initialize Azure OpenAI client: {e}")
            self._enabled = False
    
    @property
    def is_enabled(self) -> bool:
        """Check if AI service is available."""
        return self._enabled
    
    def get_status(self) -> dict:
        """Get the status of the AI service."""
        endpoint = settings.azure_openai.endpoint
        return {
            "enabled": self._enabled,
            "endpoint": endpoint[:30] + "..." if endpoint else None,
            "deployment": settings.azure_openai.deployment if self._enabled else None,
            "fallback_available": True
        }
    
    async def generate_room_description(
        self,
        room_type: str,
        room_name: str,
        room_width: int,
        room_height: int,
        furniture_count: int
    ) -> str:
        """
        Generate an atmospheric description for a single room.
        
        Args:
            room_type: Type of room (library, armory, etc.)
            room_name: Generated name of the room
            room_width: Width of the room in tiles
            room_height: Height of the room in tiles
            furniture_count: Number of furniture items in the room
        
        Returns:
            Atmospheric room description
        """
        if self._enabled and self._client:
            try:
                size_desc = "small" if room_width * room_height < 40 else "spacious" if room_width * room_height > 80 else "modest-sized"
                furniture_desc = "sparse" if furniture_count <= 2 else "moderate" if furniture_count <= 4 else "rich"
                
                # Simplified prompt for reasoning models that use many tokens internally
                prompt = f"""Generate a 2-3 sentence atmospheric description for a dungeon {room_type} called "{room_name}". 
It's {size_desc} with {furniture_desc} furnishings. Use second person. Be immersive and evocative."""

                response = await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=settings.azure_openai.deployment,
                    messages=[
                        {"role": "system", "content": "You are a dungeon master. Generate only the room description, nothing else."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=2000  # High limit needed for reasoning models (GPT-5/o1/o3) that use ~500+ tokens internally
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                print(f"[AIService] Error generating description: {e}")
        
        # Use fallback descriptions
        descriptions = FALLBACK_DESCRIPTIONS.get(room_type, FALLBACK_DESCRIPTIONS["chamber"])
        return random.choice(descriptions)
    
    async def generate_room_descriptions(self, rooms: list[dict]) -> list[dict]:
        """
        Generate descriptions for multiple rooms.
        Uses batching for efficiency when using Azure OpenAI.
        
        Args:
            rooms: List of room dictionaries with id, room_type, name, width, height, furniture
        
        Returns:
            Same list of rooms with 'description' field populated
        """
        print(f"[AIService] Generating descriptions for {len(rooms)} rooms...")
        
        # Process rooms with some concurrency but not too much to avoid rate limits
        semaphore = asyncio.Semaphore(5)
        
        async def generate_with_limit(room: dict) -> dict:
            async with semaphore:
                description = await self.generate_room_description(
                    room_type=room.get("room_type", "chamber"),
                    room_name=room.get("name", "Unknown Room"),
                    room_width=room.get("width", 10),
                    room_height=room.get("height", 10),
                    furniture_count=len(room.get("furniture", []))
                )
                room["description"] = description
                return room
        
        tasks = [generate_with_limit(room) for room in rooms]
        results = await asyncio.gather(*tasks)
        
        print(f"[AIService] Finished generating {len(results)} room descriptions")
        return results
    
    async def generate_game_name(self) -> str:
        """
        Generate a unique, evocative name for a dungeon game.
        Uses AI if available, otherwise picks from fallback names.
        
        Returns:
            A creative dungeon name
        """
        if self._enabled and self._client:
            try:
                prompt = """Generate a single creative, evocative name for a dark fantasy dungeon.
The name should be 2-4 words, mysterious, and hint at danger or ancient secrets.
Examples: "The Sunken Crypt", "Halls of the Forgotten", "Shadowmere Depths"

Generate ONLY the name, nothing else. No quotes, no explanation."""

                response = await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=settings.azure_openai.deployment,
                    messages=[
                        {"role": "system", "content": "You are a creative fantasy name generator."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=200  # Higher limit needed for reasoning models (GPT-5/o1/o3)
                )
                
                name = response.choices[0].message.content.strip().strip('"\'')
                if name and len(name) < 50:
                    return name
                    
            except Exception as e:
                print(f"[AIService] Error generating game name: {e}")
        
        # Use fallback name
        return random.choice(FALLBACK_GAME_NAMES)
    
    async def generate_player_nickname(
        self,
        kills_by_type: dict[str, int],
        total_kills: int
    ) -> str:
        """
        Generate a warrior nickname based on the player's kill statistics.
        
        Args:
            kills_by_type: Dictionary mapping monster types to kill counts
            total_kills: Total number of monsters killed
        
        Returns:
            A creative warrior title like "The Goblin Slayer"
        """
        if self._enabled and self._client and total_kills > 0:
            try:
                # Build kill summary for the prompt
                kill_summary = ", ".join([
                    f"{count} {monster_type}{'s' if count > 1 else ''}"
                    for monster_type, count in sorted(
                        kills_by_type.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]  # Top 5 monster types
                ])
                
                prompt = f"""Generate a short warrior title (2-4 words, starting with "The") for a dungeon hero who has killed:
{kill_summary}
Total kills: {total_kills}

The title should reflect their most impressive kills or fighting style.
Examples: "The Goblin Slayer", "The Undead Scourge", "The Fearless Hunter", "The Shadow Stalker"

Generate ONLY the title, nothing else. No quotes, no explanation. Must start with "The"."""

                response = await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=settings.azure_openai.deployment,
                    messages=[
                        {"role": "system", "content": "You are a fantasy title generator for warrior heroes."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=200  # Higher limit needed for reasoning models (GPT-5/o1/o3)
                )
                
                nickname = response.choices[0].message.content.strip().strip('"\'')
                # Ensure it starts with "The"
                if nickname and len(nickname) < 50:
                    if not nickname.startswith("The "):
                        nickname = f"The {nickname}"
                    return nickname
                    
            except Exception as e:
                print(f"[AIService] Error generating player nickname: {e}")
        
        # Use fallback nickname based on top kill type
        if kills_by_type:
            top_type = max(kills_by_type.keys(), key=lambda k: kills_by_type[k])
            if top_type in MONSTER_NICKNAME_TEMPLATES:
                return random.choice(MONSTER_NICKNAME_TEMPLATES[top_type])
        
        # Generic fallback
        return random.choice(FALLBACK_NICKNAMES)


# Global AI service instance
ai_service = AIService()
