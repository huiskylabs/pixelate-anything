#!/usr/bin/env python3
"""The MCP half of the gallery: drive the pixelate-anything MCP server the way an agent does
(stdio, tool calls, images back) and save what it returns into docs/gallery/mcp/.

    pip install mcp            # once
    python3 demo/mcp_demo.py   # about 3 minutes; needs ffmpeg for the MP4s

What it does, in agent order:
  1. guide('rebuild')                       read how to rebuild a place
  2. palette(ramps=...)                     plan a palette, get a swatch image back
  3. export_assets('library/projections')   one scene in five pixel-art projections
  4. export_assets('library/san-francisco') the aerial photo rebuilt (3/4) + the iso diorama
  5. export_assets('library/santorini')     a Pexels aerial rebuilt as an isometric village
     export_assets('library/retro-screens') original 8-bit and Game Boy-style screens; era(...) checks them
  6. render_audio('library/starter-music', ...) a chiptune loop for a game
Each image the server returns is what the agent would look at; they are saved as mcp/NN-*.png.
"""
import asyncio, base64, os, pathlib, shutil, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'gallery' / 'mcp'

async def main():
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        sys.exit('pip install mcp')
    OUT.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'pixelate'), 'mcp'],
                                   env=dict(os.environ, PIXELATE_WORKSPACE=str(ROOT)))
    n = 0
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = [t.name for t in (await s.list_tools()).tools]
            print('tools:', ', '.join(tools))

            async def call(tool, **args):
                nonlocal n
                t0 = time.time()
                res = await s.call_tool(tool, args)
                texts, saved = [], []
                for c in res.content:
                    if c.type == 'text':
                        texts.append(c.text)
                    elif c.type == 'image':
                        n += 1
                        p = OUT / ('%02d-%s.png' % (n, tool))
                        p.write_bytes(base64.b64decode(c.data))
                        saved.append(p.name)
                print('\n## %s(%s)  %.1fs' % (tool, ', '.join('%s=%r' % kv for kv in args.items())[:120], time.time() - t0))
                print('\n'.join(texts)[:900])
                if saved:
                    print('images back:', ', '.join(saved))
                return texts

            await call('guide', name='rebuild')
            await call('palette', action='ramps', ramps={'plaster': '#e9eef0', 'dome': '#2f6ad8', 'pool': '#4fd2e2',
                                                         'stone': '#8d6f62', 'bloom': '#d8327e'},
                       steps=5, shift=26, out='docs/gallery/palettes/santorini')
            await call('export_assets', pack='library/projections')
            await call('export_assets', pack='library/san-francisco')
            await call('export_assets', pack='library/santorini')
            await call('export_assets', pack='library/retro-screens')
            await call('era', image='library/retro-screens/out/island_village.png', era='gameboy')
            await call('era', image='library/retro-screens/out/rooftop_run.png', era='nes')
            await call('render_audio', scene='library/starter-music', out='docs/gallery/music/pixel-radio.ogg')

    # collect the animations next to the images
    for pack in ('projections', 'san-francisco', 'santorini', 'retro-screens'):
        o = ROOT / 'library' / pack / 'out'
        for f in sorted(o.glob('*')):
            if f.suffix in ('.mp4', '.gif') or f.name.endswith('@3x.png') or f.name.endswith('@2x.png'):
                shutil.copy(f, OUT / f.name)
    print('\nsaved to', OUT)

if __name__ == '__main__':
    asyncio.run(main())
