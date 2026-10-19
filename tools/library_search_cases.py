"""Labelled `pixelate find` requests against the real checked-in library.

Author-created and corpus-aware: each request was written by reading one piece's summary and tags
and phrasing what a person who wants something like it might type (the starter cases describe a
request no finished piece covers). This is an in-sample routing regression for `find`, not a
held-out or unseen-request benchmark, and says nothing about art quality. The requests were frozen
before search was tuned against them. Many manifest `request` fields are provenance notes
("Unknown: ...") or photo credits, so they were not reused as queries.

CASES: (request, expected). `expected` is a piece id that must be among the top 3 matches, or
('starter', ID): find must abstain from every finished piece and fall back to that starter.
NO_MATCH_CASES: (request, mode) requests that no finished piece is close to; find must return no
match. They are kept apart from the 20 scored cases.
"""

CASES = [
    ('a stormy canyon where two waterfalls meet, with a rope bridge and a forge glowing in the cliff',
     'canyon-cycle'),
    ('a tiny gondola carrying someone with a lantern up the trunk of an enormous tree, past a town built '
     'into the bark and on up into the clouds', 'endless-ascent'),
    ('draw the same seaside town morning as Game Boy, NES, SNES and GBA versions so I can compare the '
     'consoles', 'four-machines'),
    ('a cozy little island with a cottage and a lighthouse that loops through the four seasons, for a '
     'lofi music stream', 'lantern-isle'),
    ('a 16x16 tileset and creature sprites for a swamp level, with a boardwalk and glowing moss at night',
     'lanternmoss-mire'),
    ('rebuild this aerial photo of a medieval old-town market square in isometric, crowded with stalls and '
     'a wedding', 'market-day'),
    ('assets for a top-down farming game: grass and dirt autotiles, a little hero with a walk cycle, coins, '
     'hearts and potions', 'meadow-kit'),
    ('turn my photo of a rainy shopping street at night into pixel art, with a tram and puddle reflections',
     'monsoon-street'),
    ('show one little cottage with a well and a pond in every pixel-art projection: side, top-down, '
     'isometric, oblique', 'projections'),
    ('an arcade boss reveal: a huge rusted dredging machine bursting out of a flooded quarry while a '
     'soldier takes cover', 'quarry-wakes'),
    ('an NES-style rooftop platformer level with a courier dodging pigeons, plus a matching title screen',
     'retro-screens'),
    ('a pastel platformer loop: a courier with a scarf clinging to a sea stack under a lighthouse in a pink '
     'storm', 'rose-squall'),
    ("rebuild a drone photo of downtown San Francisco's skyscrapers as an isometric city that goes from day "
     'to night', 'san-francisco'),
    ('rebuild my aerial photo of Santorini: whitewashed houses on the caldera cliff, blue domes and a '
     'windmill', 'santorini'),
    ('pilgrims with lanterns crossing a causeway to an island monastery, a black silhouette against a low '
     'moon', 'tide-procession'),
    ("cassette cover art: a lighthouse keeper's radio on a windowsill during a storm at night",
     'tidewater-signal'),
    ('a tactics-style isometric boatyard diorama with a ship being built in a canal', 'turntable-shipyard'),
    ('a cozy ramen shop interior with steam rising on a snowy evening', ('starter', 'starter-scene-loop')),
    ('just music: a gentle chiptune loop for a puzzle game menu', ('starter', 'starter-music')),
    ('a sprite sheet of a spaceship with thruster flame frames for a vertical shooter',
     ('starter', 'starter-assets')),
]

NO_MATCH_CASES = [
    ('a neon cyberpunk alley with a samurai under a ramen stall sign', 'scene'),
    ('an underwater coral reef with jellyfish and a sunken submarine', 'scene'),
    ('a Game Boy style dungeon crawler with skeletons and torches', 'era'),
    ('rebuild this photo of my dog asleep on the sofa', 'rebuild'),
    ('a tileset for a snowy tundra with ice caves', 'assets'),
]
