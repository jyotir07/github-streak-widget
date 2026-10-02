WIDTH, HEIGHT = 1660, 260
COLUMNS = 19
TILE_SIZE, TILE_PITCH, TILE_X = 42, 55, 571
TILE_ROWS_Y = (82, 136)

LEVEL_FILLS = {
    "NONE": "#16232a",
    "FIRST_QUARTILE": "#1d3d35",
    "SECOND_QUARTILE": "#27704b",
    "THIRD_QUARTILE": "#41b06c",
    "FOURTH_QUARTILE": "#b9f7cf",
}

# Two rounded panels joined by a pinched neck, drawn as one path so the outline has no seams.
TWIN_PANEL = (
    "M71 34 H220 C248 34 256 46 264 58 C272 68 290 68 298 58 C306 46 314 34 342 34 "
    "H494 A40 40 0 0 1 534 74 V186 A40 40 0 0 1 494 226 "
    "H342 C314 226 306 214 298 202 C290 192 272 192 264 202 C256 214 248 226 220 226 "
    "H71 A40 40 0 0 1 31 186 V74 A40 40 0 0 1 71 34 Z"
)
FLAME = (
    "M52 0 C60 22 82 36 82 62 C82 86 66 100 50 100 C32 100 18 86 18 66 "
    "C18 50 24 40 30 28 C32 42 36 50 42 56 C40 36 44 16 52 0 Z"
)
FLAME_CORE = "M50 62 C58 72 60 82 56 90 C54 95 46 95 44 90 C40 82 42 72 50 62 Z"


def font_size(streak):
    digits = len(str(streak))
    if digits <= 2:
        return 128
    if digits == 3:
        return 100
    return 80


def render_tiles(levels):
    tiles = []
    for i, level in enumerate(levels):
        row, col = divmod(i, COLUMNS)
        glow = ' filter="url(#glow)"' if level == "FOURTH_QUARTILE" else ""
        tiles.append(
            f'<rect class="tile" x="{TILE_X + col * TILE_PITCH}" y="{TILE_ROWS_Y[row]}" '
            f'width="{TILE_SIZE}" height="{TILE_SIZE}" rx="9" fill="{LEVEL_FILLS[level]}"{glow}/>'
        )
    return "\n  ".join(tiles)


def render_svg(streak, levels):
    if len(levels) != len(TILE_ROWS_Y) * COLUMNS:
        raise ValueError(f"expected {len(TILE_ROWS_Y) * COLUMNS} levels, got {len(levels)}")
    tiles = render_tiles(levels)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{streak} day GitHub contribution streak">
  <title>{streak} day GitHub contribution streak</title>
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="haze" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
    <linearGradient id="badgeStroke" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#4fd1a5" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#2a4a46" stop-opacity="0.6"/>
    </linearGradient>
    <linearGradient id="panelFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#14231f"/>
      <stop offset="100%" stop-color="#0c1715"/>
    </linearGradient>
    <linearGradient id="flameFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#86f7b4"/>
      <stop offset="100%" stop-color="#2dd4bf"/>
    </linearGradient>
    <linearGradient id="numberFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#effff5"/>
      <stop offset="100%" stop-color="#a3f0c8"/>
    </linearGradient>
  </defs>
  <rect x="18" y="19" width="1624" height="222" rx="56" fill="#0a1214" fill-opacity="0.92" stroke="url(#badgeStroke)" stroke-width="2"/>
  <path d="{TWIN_PANEL}" fill="none" stroke="#4fd1a5" stroke-opacity="0.45" stroke-width="6" filter="url(#haze)"/>
  <path d="{TWIN_PANEL}" fill="url(#panelFill)" stroke="#5fe0b4" stroke-opacity="0.6" stroke-width="2"/>
  <rect x="63" y="51" width="170" height="158" rx="36" fill="#0f1c1b" stroke="#2c4c45" stroke-width="1.5"/>
  <g transform="translate(78 65) scale(1.4 1.3)" filter="url(#glow)">
    <path d="{FLAME}" fill="url(#flameFill)"/>
    <path d="{FLAME_CORE}" fill="#0f1c1b"/>
  </g>
  <text id="streak" x="416" y="176" text-anchor="middle" font-family="'Segoe UI', Inter, Arial, sans-serif" font-size="{font_size(streak)}" font-weight="700" fill="url(#numberFill)" filter="url(#glow)">{streak}</text>
  {tiles}
</svg>
'''
