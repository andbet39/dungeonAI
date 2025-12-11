# MongoDB Migration Guide for DungeonAI

This document describes the MongoDB migration implementation and how to use it.

## Overview

DungeonAI has been migrated from JSON file-based storage to MongoDB Atlas for improved scalability, concurrency, and data management.

### What Changed

- **Game saves** → MongoDB `games` collection
- **Player registry & stats** → MongoDB `players` and `player_stats` collections
- **AI Q-learning tables** → MongoDB `species_knowledge` collection (stored as Binary for efficiency)
- **AI learning history** → MongoDB `species_history` collection
- **Spawn rates config** → MongoDB `spawn_rates` collection
- **Sandbox state** → MongoDB `sandbox` collection

### What Stayed the Same

- **monsters.json** remains as a JSON file (per requirements)
- **Fallback support** - Application still works with JSON if MongoDB is unavailable

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `motor>=3.3.0` (async MongoDB driver)
- `pymongo>=4.5.0` (MongoDB Python driver)

### 2. Configure MongoDB

#### Option A: MongoDB Atlas (Recommended)

1. Create a free MongoDB Atlas cluster at https://www.mongodb.com/cloud/atlas
2. Add IP whitelist: `0.0.0.0/0` (for Render.com deployment)
3. Create a database user with read/write permissions
4. Get your connection string

#### Option B: Local MongoDB

```bash
# Install MongoDB locally
brew install mongodb-community  # macOS
# or follow https://docs.mongodb.com/manual/installation/

# Start MongoDB
brew services start mongodb-community
```

### 3. Set Environment Variables

Create or update your `.env` file:

```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=dungeonai_db

# Existing configurations...
```

For local MongoDB:
```bash
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/
MONGODB_DATABASE=dungeonai_db
```

## Migration Process

### Step 1: Test Connection

```bash
python backend/scripts/migrate_to_mongodb.py "$MONGODB_CONNECTION_STRING" --dry-run
```

This performs a dry run without writing data, verifying:
- MongoDB connection works
- All JSON files can be read
- Data structures are valid

### Step 2: Run Migration

```bash
python backend/scripts/migrate_to_mongodb.py "$MONGODB_CONNECTION_STRING"
```

The script will:
1. Connect to MongoDB
2. Migrate all game saves
3. Migrate player registry and stats
4. Migrate AI Q-learning tables (~6.8MB)
5. Migrate AI learning history
6. Migrate spawn rates configuration
7. Migrate sandbox state
8. Verify all data was migrated correctly

### Step 3: Verify Migration

The script outputs verification counts:

```
Database Contents:
  • Games:             5
  • Players:           10
  • Player Stats:      10
  • Species Knowledge: 4
  • Species History:   4
  • Spawn Rates:       1
  • Sandbox:           1
```

### Step 4: Update Deployment

#### Render.com

1. Go to your Render dashboard
2. Navigate to Environment section
3. Add environment variables:
   - `MONGODB_CONNECTION_STRING`: Your MongoDB Atlas connection string
   - `MONGODB_DATABASE`: `dungeonai_db`
4. Trigger a new deployment

#### Local Development

1. Ensure `.env` has MongoDB variables
2. Restart the application:
   ```bash
   ./start.sh
   ```

### Step 5: Verify Application

1. Start the application
2. Check logs for MongoDB connection:
   ```
   [Main] MongoDB connected: dungeonai_db
   [MonsterService] Using MongoDB species knowledge store
   ```
3. Test game functionality:
   - Create a new game
   - Join existing games
   - Verify AI learning persists

## Architecture

### Dual Storage Pattern

The application uses a dual storage pattern with automatic backend selection:

```python
# Storage backend auto-selection
if settings.mongodb.is_enabled and mongodb_manager.is_connected:
    storage_service = MongoDBStorageService()  # Use MongoDB
else:
    storage_service = StorageService()  # Fallback to JSON
```

This ensures:
- **Zero downtime** - Application works during migration
- **Graceful degradation** - Falls back to JSON if MongoDB unavailable
- **Backward compatibility** - Existing JSON files still work

### MongoDB Collections Schema

#### games
```javascript
{
  game_id: String (unique index),
  name: String,
  saved_at: ISODate,
  save_reason: String,
  map: { width, height, tiles, spawn_x, spawn_y, seed },
  rooms: [...],
  players: {...},
  monsters: {...},
  created_at: ISODate (index),
  last_activity: ISODate (index)
}
```

#### species_knowledge
```javascript
{
  monster_type: String (unique index),
  generation: Number,
  encounters: Number,
  total_learning_steps: Number,
  q_table_shape: [Number, Number],
  q_table: Binary,  // NumPy array as bytes
  schema_version: Number (index),
  created_at: ISODate,
  last_updated: ISODate
}
```

#### players & player_stats
```javascript
// players collection
{
  token: String (unique index),
  display_name: String,
  nickname: String,
  current_game_id: String,
  updated_at: ISODate
}

// player_stats collection
{
  token: String (unique index),
  experience_earned: Number (desc index),  // For leaderboard
  kills_by_type: {...},
  damage_dealt: Number,
  damage_taken: Number,
  deaths: Number,
  updated_at: ISODate
}
```

## Monitoring

### Application Logs

Monitor MongoDB connection status:
```bash
tail -f logs/dungeonai.log | grep MongoDB
```

Expected logs:
- `[MongoDB] Connected to database: dungeonai_db`
- `[MongoDB] Indexes created successfully`
- `[MongoDBStorage] Saved game {game_id}`
- `[MongoDBSpeciesStore] Loaded 4 species records`

### MongoDB Atlas Monitoring

1. Go to MongoDB Atlas dashboard
2. View Metrics tab for:
   - Connection count
   - Operations per second
   - Document count
   - Storage size

## Troubleshooting

### Connection Issues

**Error:** `MongoDB not connected`

**Solutions:**
1. Verify `MONGODB_CONNECTION_STRING` is set correctly
2. Check IP whitelist in MongoDB Atlas (add `0.0.0.0/0`)
3. Verify database user has read/write permissions
4. Check connection string format:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/
   ```

### Migration Failures

**Error:** Migration script fails partway through

**Solutions:**
1. Check JSON file permissions
2. Verify MongoDB user has write permissions
3. Run with `--dry-run` first to identify issues
4. Check disk space on MongoDB cluster

### Performance Issues

**Slow saves/loads after migration**

**Solutions:**
1. Verify indexes were created (check MongoDB Atlas)
2. Check MongoDB cluster tier (M0 free tier has limits)
3. Enable connection pooling (already configured):
   ```python
   maxPoolSize=50, minPoolSize=10
   ```

### Rollback to JSON

If needed, temporarily disable MongoDB:

```bash
# Remove or comment out MongoDB environment variables
# MONGODB_CONNECTION_STRING=...

# Restart application - will use JSON fallback
./start.sh
```

Application will automatically fall back to JSON files.

## Backup Strategy

### Before Migration

```bash
# Backup all JSON files
tar -czf dungeonai-json-backup-$(date +%Y%m%d).tar.gz backend/app/saves backend/app/config/data
```

### After Migration

- **Keep JSON backups for 7+ days**
- MongoDB Atlas provides automatic backups (check your cluster settings)
- For manual backups:
  ```bash
  mongodump --uri="$MONGODB_CONNECTION_STRING" --out=backup-$(date +%Y%m%d)
  ```

## Performance Improvements

Compared to JSON file storage:

- **Concurrent writes:** MongoDB handles multiple simultaneous game saves
- **Faster queries:** Indexed lookups for games, players, leaderboards
- **Scalability:** No file system limits on game count
- **Atomic operations:** No corruption from partial writes
- **Query capabilities:** Can query games by date, players, stats, etc.

### Query Examples

```python
# Find all active games
active_games = await db.games.find({"last_activity": {"$gte": one_hour_ago}})

# Get top players by XP
leaderboard = await db.player_stats.find().sort("experience_earned", -1).limit(10)

# Find games with specific players
games_with_player = await db.games.find({"players.token123": {"$exists": True}})
```

## Testing

Run unit tests:

```bash
cd backend
pytest tests/test_mongodb_storage.py
pytest tests/test_mongodb_species_store.py
```

Integration testing:
```bash
# Start with MongoDB configured
./start.sh

# Run game tests
pytest tests/test_game_integration.py
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-repo/dungeonai/issues
- Check logs in `backend/logs/`
- MongoDB Atlas support: https://support.mongodb.com/

## Future Enhancements

Potential improvements:
- [ ] Real-time data sync between clients via MongoDB Change Streams
- [ ] Advanced analytics queries on player behavior
- [ ] Time-series data for AI learning progression
- [ ] Sharding for horizontal scaling
- [ ] Full-text search on game names/descriptions
