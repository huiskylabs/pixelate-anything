"""Greyscale block-in of image A at native size: one grey per value band, no detail."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
from canvas import Canvas

W, H = 304, 224
G = {'darkest': '#0e0e0e', 'dark': '#2c2c2c', 'mid': '#707070', 'bright': '#e4e4e4'}

def main(out):
    c = Canvas(W, H, 'dark')
    # world: sky, walls and water share the dark band; the near rim and crane are darkest
    c.poly([(196, 192), (240, 188), (304, 184), (304, 224), (190, 224)], 'darkest')    # near rim
    c.poly([(0, 208), (20, 205), (34, 214), (36, 224), (0, 224)], 'darkest')           # outcrop
    c.poly([(204, 196), (300, 170), (304, 176), (304, 184), (210, 202)], 'darkest')    # crane boom
    c.rect(282, 170, 304, 188, 'darkest')                                              # tipped cab
    # boss: hull, cabin, stack, gantry, jaw, links, legs (mid)
    c.poly([(50, 120), (180, 120), (194, 134), (190, 166), (46, 166), (42, 134)], 'mid')  # hull
    c.rect(72, 80, 122, 120, 'mid')                                                     # cabin
    c.poly([(53, 24), (66, 22), (68, 120), (56, 120)], 'mid')                           # stack
    c.poly([(140, 120), (150, 42), (164, 42), (176, 120)], 'mid')                       # gantry
    c.poly([(150, 40), (166, 44), (228, 92), (220, 104)], 'mid')                        # jaw
    c.rect(219, 102, 229, 150, 'mid')                                                   # bucket links
    c.poly([(176, 146), (200, 128), (210, 134), (214, 168), (202, 170), (198, 140), (184, 154)], 'mid')
    c.poly([(48, 146), (60, 150), (44, 180), (34, 176)], 'mid')                         # rear leg
    # soldier (mid) crouched above the boom
    c.poly([(264, 168), (276, 160), (284, 164), (288, 186), (262, 190)], 'mid')
    # brightest: the cracked window and the spray at the waterline and the bucket cascade
    c.rect(98, 92, 107, 99, 'bright')
    for x0, y0, x1, y1 in ((40, 156, 70, 166), (76, 150, 96, 162), (120, 152, 150, 164),
                           (160, 148, 196, 166), (214, 150, 232, 170), (54, 140, 62, 152),
                           (178, 136, 186, 148)):
        c.rect(x0, y0, x1, y1, 'bright')
    c.image(G).save(out)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out/blockin-a.png')
