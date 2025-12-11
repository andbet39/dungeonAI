"""
Game persistence service for saving/loading complete game state.
Handles JSON serialization of map, rooms, players, and metadata.
Supports per-game saves and player registry.
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import settings


class StorageService:
    """Handles game state persistence to disk."""
    
    _instance: Optional["StorageService"] = None
    
    def __new__(cls) -> "StorageService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.save_path = settings.storage.save_path
        self.games_path = settings.storage.games_path
        self.players_file = settings.storage.players_file
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.games_path.mkdir(parents=True, exist_ok=True)
        self._save_lock = asyncio.Lock()
        self._initialized = True
    
    def _get_save_file(self, save_id: str = "current") -> Path:
        """Get path to a save file (legacy)."""
        return self.save_path / f"{save_id}.json"
    
    def _get_game_save_file(self, game_id: str) -> Path:
        """Get path to a per-game save file."""
        return self.games_path / f"{game_id}.json"
    
    # ============== Per-Game Save Methods ==============
    
    async def save_game_by_id(
        self,
        game_id: str,
        game_state: dict,
        reason: str = "manual"
    ) -> bool:
        """Save game state to per-game file."""
        async with self._save_lock:
            try:
                save_data = {
                    "version": "2.0",
                    "game_id": game_id,
                    "saved_at": datetime.now().isoformat(),
                    "save_reason": reason,
                    "game_state": game_state
                }
                
                save_file = self._get_game_save_file(game_id)
                temp_file = save_file.with_suffix(".tmp")
                
                def write_file():
                    with open(temp_file, "w") as f:
                        json.dump(save_data, f, indent=2)
                    temp_file.rename(save_file)
                
                await asyncio.to_thread(write_file)
                print(f"[StorageService] Saved game {game_id} (reason: {reason})")
                return True
                
            except Exception as e:
                print(f"[StorageService] Error saving game {game_id}: {e}")
                return False
    
    async def load_game_by_id(self, game_id: str) -> Optional[dict]:
        """Load game state from per-game file."""
        try:
            save_file = self._get_game_save_file(game_id)
            
            if not save_file.exists():
                return None
            
            def read_file():
                with open(save_file, "r") as f:
                    return json.load(f)
            
            save_data = await asyncio.to_thread(read_file)
            print(f"[StorageService] Loaded game {game_id}")
            return save_data.get("game_state")
            
        except Exception as e:
            print(f"[StorageService] Error loading game {game_id}: {e}")
            return None
    
    async def delete_game_save(self, game_id: str) -> bool:
        """Delete a per-game save file."""
        try:
            save_file = self._get_game_save_file(game_id)
            if save_file.exists():
                await asyncio.to_thread(save_file.unlink)
                print(f"[StorageService] Deleted game save: {game_id}")
                return True
            return False
        except Exception as e:
            print(f"[StorageService] Error deleting game {game_id}: {e}")
            return False
    
    def list_game_saves(self) -> list[dict]:
        """List all per-game save files."""
        saves = []
        for save_file in self.games_path.glob("*.json"):
            try:
                with open(save_file, "r") as f:
                    save_data = json.load(f)
                saves.append({
                    "game_id": save_file.stem,
                    "file": str(save_file),
                    "version": save_data.get("version"),
                    "saved_at": save_data.get("saved_at"),
                    "name": save_data.get("game_state", {}).get("name", "Unknown")
                })
            except Exception:
                continue
        return sorted(saves, key=lambda x: x.get("saved_at", ""), reverse=True)
    
    # ============== Player Registry Methods ==============
    
    async def save_player_registry(self, registry_data: dict) -> bool:
        """Save player registry to disk."""
        async with self._save_lock:
            try:
                save_data = {
                    "version": "1.0",
                    "saved_at": datetime.now().isoformat(),
                    "registry": registry_data
                }
                
                temp_file = self.players_file.with_suffix(".tmp")
                
                def write_file():
                    with open(temp_file, "w") as f:
                        json.dump(save_data, f, indent=2)
                    temp_file.rename(self.players_file)
                
                await asyncio.to_thread(write_file)
                return True
                
            except Exception as e:
                print(f"[StorageService] Error saving player registry: {e}")
                return False
    
    async def load_player_registry(self) -> Optional[dict]:
        """Load player registry from disk."""
        try:
            if not self.players_file.exists():
                return None
            
            def read_file():
                with open(self.players_file, "r") as f:
                    return json.load(f)
            
            save_data = await asyncio.to_thread(read_file)
            return save_data.get("registry")
            
        except Exception as e:
            print(f"[StorageService] Error loading player registry: {e}")
            return None
    
    # ============== Legacy Methods ==============
    
    async def save_game(
        self,
        game_state: dict,
        save_id: str = "current",
        reason: str = "manual"
    ) -> bool:
        """
        Save complete game state to disk.
        
        Args:
            game_state: Dictionary containing complete game state
            save_id: Identifier for the save file
            reason: Reason for saving (for logging)
        
        Returns:
            True if save was successful
        """
        async with self._save_lock:
            try:
                save_data = {
                    "version": "1.0",
                    "saved_at": datetime.now().isoformat(),
                    "save_reason": reason,
                    "game_state": game_state
                }
                
                save_file = self._get_save_file(save_id)
                
                # Write to temp file first, then rename (atomic write)
                temp_file = save_file.with_suffix(".tmp")
                
                def write_file():
                    with open(temp_file, "w") as f:
                        json.dump(save_data, f, indent=2)
                    temp_file.rename(save_file)
                
                await asyncio.to_thread(write_file)
                
                print(f"[StorageService] Saved game to {save_file} (reason: {reason})")
                return True
                
            except Exception as e:
                print(f"[StorageService] Error saving game: {e}")
                return False
    
    async def load_game(self, save_id: str = "current") -> Optional[dict]:
        """
        Load game state from disk.
        
        Args:
            save_id: Identifier of the save file to load
        
        Returns:
            Game state dictionary, or None if load failed
        """
        try:
            save_file = self._get_save_file(save_id)
            
            if not save_file.exists():
                print(f"[StorageService] No save file found: {save_file}")
                return None
            
            def read_file():
                with open(save_file, "r") as f:
                    return json.load(f)
            
            save_data = await asyncio.to_thread(read_file)
            
            print(f"[StorageService] Loaded game from {save_file}")
            print(f"[StorageService] Save version: {save_data.get('version')}, saved at: {save_data.get('saved_at')}")
            
            return save_data.get("game_state")
            
        except Exception as e:
            print(f"[StorageService] Error loading game: {e}")
            return None
    
    def list_saves(self) -> list[dict]:
        """
        List all available save files.
        
        Returns:
            List of save metadata dictionaries
        """
        saves = []
        
        for save_file in self.save_path.glob("*.json"):
            try:
                with open(save_file, "r") as f:
                    save_data = json.load(f)
                
                saves.append({
                    "id": save_file.stem,
                    "file": str(save_file),
                    "version": save_data.get("version"),
                    "saved_at": save_data.get("saved_at"),
                    "save_reason": save_data.get("save_reason"),
                    "map_width": save_data.get("game_state", {}).get("map", {}).get("width"),
                    "map_height": save_data.get("game_state", {}).get("map", {}).get("height"),
                    "room_count": len(save_data.get("game_state", {}).get("rooms", []))
                })
            except Exception as e:
                print(f"[StorageService] Error reading save file {save_file}: {e}")
                continue
        
        saves.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        return saves
    
    async def delete_save(self, save_id: str) -> bool:
        """
        Delete a save file.
        
        Args:
            save_id: Identifier of the save to delete
        
        Returns:
            True if deletion was successful
        """
        try:
            save_file = self._get_save_file(save_id)
            if save_file.exists():
                await asyncio.to_thread(save_file.unlink)
                print(f"[StorageService] Deleted save: {save_file}")
                return True
            return False
        except Exception as e:
            print(f"[StorageService] Error deleting save: {e}")
            return False
    
    async def create_backup(self, save_id: str = "current") -> Optional[str]:
        """
        Create a backup of a save file.
        
        Args:
            save_id: Identifier of the save to backup
        
        Returns:
            Backup save ID, or None if backup failed
        """
        try:
            game_state = await self.load_game(save_id)
            if not game_state:
                return None
            
            backup_id = f"backup_{save_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            success = await self.save_game(game_state, backup_id, reason="backup")
            
            return backup_id if success else None
            
        except Exception as e:
            print(f"[StorageService] Error creating backup: {e}")
            return None


# Global storage service instance
_storage_service_singleton = StorageService()


class _StorageModuleProxy:
    def __getattr__(self, name):
        return getattr(_storage_service_singleton, name)


# Module-level name used by `from . import storage_service`
storage_service = _StorageModuleProxy()


# Module-level __getattr__ for backwards compatibility if the module is imported directly
def __getattr__(name):
    return getattr(_storage_service_singleton, name)
