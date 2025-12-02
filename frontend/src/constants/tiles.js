/**
 * Tile type constants matching backend tile definitions
 */
export const TILE = {
  FLOOR: 0,
  WALL: 1,
  DOOR_CLOSED: 2,
  DOOR_OPEN: 3,
  CHEST: 4,
  TABLE: 5,
  CHAIR: 6,
  BED: 7,
  BOOKSHELF: 8,
  BARREL: 9,
  TORCH: 10,
  VOID: 11
}

/**
 * Tile rendering configuration for ROT.js display
 * Each tile has: char (display character), fg (foreground color), bg (background color)
 */
export const TILE_RENDER = {
  [TILE.VOID]: { char: ' ', fg: '#000', bg: '#000' },
  [TILE.FLOOR]: { char: '.', fg: '#555', bg: '#000' },
  [TILE.WALL]: { char: '#', fg: '#888', bg: '#333' },
  [TILE.DOOR_CLOSED]: { char: '+', fg: '#a52', bg: '#321' },
  [TILE.DOOR_OPEN]: { char: '/', fg: '#a52', bg: '#000' },
  [TILE.CHEST]: { char: '≡', fg: '#ffd700', bg: '#000' },
  [TILE.TABLE]: { char: 'π', fg: '#8b4513', bg: '#000' },
  [TILE.CHAIR]: { char: 'h', fg: '#8b4513', bg: '#000' },
  [TILE.BED]: { char: '=', fg: '#8b4513', bg: '#000' },
  [TILE.BOOKSHELF]: { char: '▐', fg: '#8b4513', bg: '#000' },
  [TILE.BARREL]: { char: '○', fg: '#8b4513', bg: '#000' },
  [TILE.TORCH]: { char: '*', fg: '#ffa500', bg: '#110' }
}

/**
 * Legend items for UI display
 */
export const TILE_LEGEND = [
  // Environment
  { char: '.', color: '#555', label: 'Floor' },
  { char: '#', color: '#888', label: 'Wall' },
  { char: '+', color: '#a52', label: 'Door (Closed)' },
  { char: '/', color: '#a52', label: 'Door (Open)' },
  { char: '≡', color: '#ffd700', label: 'Chest' },
  { char: '*', color: '#ffa500', label: 'Torch' },
  // Monsters
  { char: 'g', color: '#2ecc71', label: 'Goblin' },
  { char: 's', color: '#ecf0f1', label: 'Skeleton' },
  { char: 'O', color: '#8b4513', label: 'Orc' },
  { char: 'Z', color: '#556b2f', label: 'Zombie' },
  { char: 'S', color: '#2c3e50', label: 'Giant Spider' },
  { char: 'k', color: '#e67e22', label: 'Kobold' },
  { char: 'G', color: '#a8d8ea', label: 'Ghost' },
  { char: 'r', color: '#7f8c8d', label: 'Rat Swarm' },
  { char: 'C', color: '#9b59b6', label: 'Dark Cultist' },
  { char: 'M', color: '#d4a574', label: 'Mimic' },
  { char: 'j', color: '#27ae60', label: 'Slime' },
  { char: 'B', color: '#c0392b', label: 'Bandit' }
]
