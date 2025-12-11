#!/usr/bin/env python3
"""
MongoDB Migration Script for DungeonAI

Migrates all JSON-based data to MongoDB Atlas.

Usage:
    python migrate_to_mongodb.py <connection_string> [--dry-run]

Example:
    python migrate_to_mongodb.py "mongodb+srv://user:pass@cluster.mongodb.net/" --dry-run
    python migrate_to_mongodb.py "mongodb+srv://user:pass@cluster.mongodb.net/"
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import Binary
import numpy as np


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_phase(phase_num: int, total: int, text: str):
    """Print a phase header."""
    print(f"\n[{phase_num}/{total}] {text}")
    print("-" * 70)


async def migrate_json_to_mongodb(
    json_base_path: str,
    config_data_path: str,
    mongodb_connection: str,
    database_name: str = "dungeonai_db",
    dry_run: bool = False
):
    """Migrate all JSON data to MongoDB."""

    print_header("DungeonAI MongoDB Migration Tool")

    if dry_run:
        print("DRY RUN MODE - No data will be written to MongoDB\n")

    # Connect to MongoDB
    print(f"Connecting to MongoDB...")
    client = AsyncIOMotorClient(mongodb_connection)
    db = client[database_name]

    try:
        await client.admin.command('ping')
        print(f"✓ Connected to MongoDB database: {database_name}\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    base_path = Path(json_base_path)
    config_path = Path(config_data_path)

    # Track statistics
    stats = {
        "games": 0,
        "players": 0,
        "player_stats": 0,
        "species_knowledge": 0,
        "species_history": 0,
        "spawn_rates": 0,
        "sandbox": 0,
    }

    # ============== Phase 1: Migrate Game Saves ==============
    print_phase(1, 6, "Migrating Game Saves")

    games_path = base_path / "games"
    if games_path.exists():
        game_files = list(games_path.glob("*.json"))
        print(f"Found {len(game_files)} game save file(s)")

        for game_file in game_files:
            try:
                with open(game_file, "r") as f:
                    data = json.load(f)

                game_state = data.get("game_state", {})
                save_doc = {
                    "game_id": data.get("game_id", game_file.stem),
                    "saved_at": datetime.fromisoformat(data.get("saved_at", datetime.now().isoformat())),
                    "save_reason": data.get("save_reason", "migration"),
                    **game_state
                }

                if not dry_run:
                    await db.games.update_one(
                        {"game_id": save_doc["game_id"]},
                        {"$set": save_doc},
                        upsert=True
                    )

                stats["games"] += 1
                print(f"  ✓ Migrated game: {save_doc['game_id']}")

            except Exception as e:
                print(f"  ✗ Error migrating {game_file.name}: {e}")

        print(f"\n✓ Migrated {stats['games']} game save(s)")
    else:
        print("  No games directory found, skipping")

    # ============== Phase 2: Migrate Player Registry ==============
    print_phase(2, 6, "Migrating Player Registry")

    players_file = base_path / "players.json"
    if players_file.exists():
        try:
            with open(players_file, "r") as f:
                registry_data = json.load(f)

            players_data = registry_data.get("registry", {}).get("players", {})
            stats_data = registry_data.get("registry", {}).get("stats", {})

            # Migrate players
            if players_data and not dry_run:
                from pymongo import UpdateOne

                player_ops = [
                    UpdateOne(
                        {"token": token},
                        {"$set": {**data, "token": token, "updated_at": datetime.now()}},
                        upsert=True
                    )
                    for token, data in players_data.items()
                ]
                if player_ops:
                    await db.players.bulk_write(player_ops)

            stats["players"] = len(players_data)

            # Migrate player stats
            if stats_data and not dry_run:
                from pymongo import UpdateOne

                stat_ops = [
                    UpdateOne(
                        {"token": token},
                        {"$set": {**data, "token": token, "updated_at": datetime.now()}},
                        upsert=True
                    )
                    for token, data in stats_data.items()
                ]
                if stat_ops:
                    await db.player_stats.bulk_write(stat_ops)

            stats["player_stats"] = len(stats_data)

            print(f"  ✓ Migrated {stats['players']} player(s)")
            print(f"  ✓ Migrated {stats['player_stats']} player stat record(s)")
            print(f"\n✓ Player registry migration complete")

        except Exception as e:
            print(f"  ✗ Error migrating player registry: {e}")
    else:
        print("  No players.json found, skipping")

    # ============== Phase 3: Migrate Species Knowledge (Q-Tables) ==============
    print_phase(3, 6, "Migrating Species Knowledge (AI Q-Tables)")

    species_file = config_path / "species_knowledge.json"
    if species_file.exists():
        try:
            file_size_mb = species_file.stat().st_size / 1024 / 1024
            print(f"  Loading species knowledge file ({file_size_mb:.1f} MB)...")

            with open(species_file, "r") as f:
                species_data = json.load(f)

            schema_version = species_data.get("_schema_version", 1)
            print(f"  Schema version: {schema_version}")

            from pymongo import UpdateOne
            ops = []

            for monster_type, data in species_data.items():
                if monster_type.startswith("_"):
                    continue

                # Convert Q-table to numpy and serialize to binary
                q_table = np.array(data["q_table"], dtype=np.float32)
                q_table_binary = Binary(q_table.tobytes())

                q_size_kb = len(q_table_binary) / 1024

                doc = {
                    "monster_type": monster_type,
                    "generation": data.get("generation", 0),
                    "encounters": data.get("encounters", 0),
                    "total_learning_steps": data.get("total_learning_steps", 0),
                    "q_table_shape": list(q_table.shape),
                    "q_table": q_table_binary,
                    "schema_version": schema_version,
                    "created_at": datetime.now(),
                    "last_updated": datetime.now()
                }

                ops.append(UpdateOne(
                    {"monster_type": monster_type},
                    {"$set": doc},
                    upsert=True
                ))

                stats["species_knowledge"] += 1
                print(f"  ✓ {monster_type}: Q-table {q_table.shape} ({q_size_kb:.1f} KB)")

            if ops and not dry_run:
                result = await db.species_knowledge.bulk_write(ops)
                print(f"\n  Inserted/updated: {result.upserted_count + result.modified_count} document(s)")

            print(f"\n✓ Migrated {stats['species_knowledge']} species Q-table(s)")

        except Exception as e:
            print(f"  ✗ Error migrating species knowledge: {e}")
    else:
        print("  No species_knowledge.json found, skipping")

    # ============== Phase 4: Migrate Species History ==============
    print_phase(4, 6, "Migrating Species Learning History")

    history_dir = config_path / "species_history"
    if history_dir.exists():
        history_files = list(history_dir.glob("*.json"))
        print(f"Found {len(history_files)} species history file(s)")

        for history_file in history_files:
            try:
                with open(history_file, "r") as f:
                    history_data = json.load(f)

                # Convert ISO timestamp strings to datetime objects
                history = history_data.get("history", [])
                for entry in history:
                    if "timestamp" in entry and isinstance(entry["timestamp"], str):
                        try:
                            entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
                        except:
                            entry["timestamp"] = datetime.now()

                doc = {
                    "monster_type": history_data["monster_type"],
                    "schema_version": history_data.get("schema_version", 1),
                    "history": history,
                    "last_updated": datetime.now()
                }

                if not dry_run:
                    await db.species_history.update_one(
                        {"monster_type": doc["monster_type"]},
                        {"$set": doc},
                        upsert=True
                    )

                stats["species_history"] += 1
                entries_count = len(history)
                print(f"  ✓ {history_data['monster_type']}: {entries_count} history entries")

            except Exception as e:
                print(f"  ✗ Error migrating {history_file.name}: {e}")

        print(f"\n✓ Migrated {stats['species_history']} species history file(s)")
    else:
        print("  No species_history directory found, skipping")

    # ============== Phase 5: Migrate Spawn Rates Config ==============
    print_phase(5, 6, "Migrating Spawn Rates Configuration")

    spawn_rates_file = config_path / "spawn_rates.json"
    if spawn_rates_file.exists():
        try:
            with open(spawn_rates_file, "r") as f:
                spawn_data = json.load(f)

            doc = {
                "config_version": "1.0",
                **spawn_data,
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }

            if not dry_run:
                await db.spawn_rates.update_one(
                    {"config_version": "1.0"},
                    {"$set": doc},
                    upsert=True
                )

            stats["spawn_rates"] = 1
            print(f"  ✓ Migrated spawn rates configuration")

        except Exception as e:
            print(f"  ✗ Error migrating spawn rates: {e}")
    else:
        print("  No spawn_rates.json found, skipping")

    # ============== Phase 6: Migrate Sandbox State ==============
    print_phase(6, 6, "Migrating Sandbox State")

    sandbox_file = base_path / "sandbox.json"
    if sandbox_file.exists():
        try:
            with open(sandbox_file, "r") as f:
                sandbox_data = json.load(f)

            doc = {
                "singleton": "sandbox",
                **sandbox_data,
                "last_updated": datetime.now()
            }

            if not dry_run:
                await db.sandbox.update_one(
                    {"singleton": "sandbox"},
                    {"$set": doc},
                    upsert=True
                )

            stats["sandbox"] = 1
            print(f"  ✓ Migrated sandbox state")

        except Exception as e:
            print(f"  ✗ Error migrating sandbox: {e}")
    else:
        print("  No sandbox.json found, skipping")

    # ============== Verification ==============
    print_header("Migration Summary")

    if not dry_run:
        # Verify counts
        actual_counts = {
            "games": await db.games.count_documents({}),
            "players": await db.players.count_documents({}),
            "player_stats": await db.player_stats.count_documents({}),
            "species_knowledge": await db.species_knowledge.count_documents({}),
            "species_history": await db.species_history.count_documents({}),
            "spawn_rates": await db.spawn_rates.count_documents({}),
            "sandbox": await db.sandbox.count_documents({}),
        }

        print("Database Contents:")
        print(f"  • Games:             {actual_counts['games']}")
        print(f"  • Players:           {actual_counts['players']}")
        print(f"  • Player Stats:      {actual_counts['player_stats']}")
        print(f"  • Species Knowledge: {actual_counts['species_knowledge']}")
        print(f"  • Species History:   {actual_counts['species_history']}")
        print(f"  • Spawn Rates:       {actual_counts['spawn_rates']}")
        print(f"  • Sandbox:           {actual_counts['sandbox']}")

        print_header("Migration Completed Successfully!")
        print("Next steps:")
        print("1. Set MONGODB_CONNECTION_STRING environment variable")
        print("2. Restart your application")
        print("3. Verify data loads correctly")
        print("4. Keep JSON backups for at least 7 days")
    else:
        print("DRY RUN - No data was written to MongoDB")
        print("\nMigrated (would have migrated):")
        print(f"  • Games:             {stats['games']}")
        print(f"  • Players:           {stats['players']}")
        print(f"  • Player Stats:      {stats['player_stats']}")
        print(f"  • Species Knowledge: {stats['species_knowledge']}")
        print(f"  • Species History:   {stats['species_history']}")
        print(f"  • Spawn Rates:       {stats['spawn_rates']}")
        print(f"  • Sandbox:           {stats['sandbox']}")
        print("\nRun without --dry-run to perform actual migration")

    client.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    connection_string = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    # Default paths (adjust if needed)
    json_path = "backend/app/saves"
    config_path = "backend/app/config/data"

    asyncio.run(migrate_json_to_mongodb(
        json_path,
        config_path,
        connection_string,
        dry_run=dry_run
    ))


if __name__ == "__main__":
    main()
