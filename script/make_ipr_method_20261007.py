# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# (a-d) method schematic -> other/ has no matching script -> custom vector layout
# Photos and endpoint predictions are real; diagram maps are explicitly schematic.
from pathlib import Path
import json
import matplotlib as mpl
mpl.use('Agg')
mpl.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'Liberation Sans'],
    'font.size': 8, 'axes.titlesize': 8, 'axes.labelsize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 8,
    'figure.titlesize': 9, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.linewidth': 0.6, 'xtick.direction': 'out', 'ytick.direction': 'out',
    'xtick.major.width': 0.6, 'ytick.major.width': 0.6, 'legend.frameon': False,
})
CATEGORICAL = ['#2166AC', '#B2182B', '#1B7837', '#F1A340', '#762A83', '#666666']
CATEGORICAL_EXTENDED = ['#2166AC', '#B2182B', '#1B7837', '#F1A340', '#762A83', '#666666', '#4393C3', '#D6604D', '#5AAE61', '#B35806', '#9970AB', '#999999']
DIVERGING = ['#2166AC', '#F7F7F7', '#B2182B']
SEQUENTIAL = ['#F7FBFF', '#6BAED6', '#08306B']
ACCENT_RED = '#B2182B'
GREY = '#999999'
BLACK = '#222222'
mpl.rcParams.update({'pdf.fonttype': 42, 'svg.fonttype': 'none', 'savefig.bbox': 'tight', 'savefig.dpi': 300})
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Ellipse, FancyArrowPatch
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/method_figure_20261007'
OUT.mkdir(parents=True, exist_ok=True)
fig = plt.figure(figsize=(183 / 25.4, 155 / 25.4), facecolor='white')
ax = fig.add_axes([0, 0, 1, 1])
ax.set(xlim=(0, 183), ylim=(155, 0))
ax.axis('off')
ink, green, blue = '#25323A', '#177560', '#2166AC'

def txt(x, y, s, size=7, color=ink, bold=False, ha='left'):
    return ax.text(x, y, s, fontsize=size, color=color, weight='bold' if bold else 'normal', ha=ha, va='center', linespacing=1.25)

def box(x,y,w,h,fill,edge='#BAC7CC'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=1.5',fc=fill,ec=edge,lw=.7))

def arrow(x1,y1,x2,y2,color=ink,dash=False):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=8,lw=.9,color=color,linestyle='--' if dash else '-'))

def pic(path,x,y,w,h):
    a = fig.add_axes([x/183,1-(y+h)/155,w/183,h/155])
    a.imshow(Image.open(path)); a.axis('off')
    return a

def maps(x,y,w,h,mode='raw'):
    # Abstract regions, deliberately not fitted to a photographic scene.
    ax.add_patch(Rectangle((x,y),w,h,facecolor='#E6E9EA',edgecolor='white',lw=.4))
    colors=['#4393C3','#F1A340','#9970AB']
    shapes=[(.25,.43,.34,.61),(.66,.30,.37,.40),(.65,.74,.51,.27)]
    if mode=='confidence': colors=['#246E9C','#B9D8E8','#659FBF']
    for (xx,yy,ww,hh),c in zip(shapes,colors):
        ax.add_patch(Ellipse((x+xx*w,y+yy*h),ww*w,hh*h,angle=12,fc=c,ec='white',lw=.5))
    if mode=='raw':
        for xx,yy in [(0.12,.85),(.9,.14),(.45,.15)]:
            ax.add_patch(Rectangle((x+xx*w,y+yy*h),w*.06,h*.08,fc=colors[0],ec='none'))
    if mode=='confidence':
        ax.add_patch(Ellipse((x+.25*w,y+.43*h),w*.34,h*.61,angle=12,fc='none',ec='#CDE5EF',lw=1.5))

txt(4,5,'Identity-preserving pseudo-label reliability modeling',10,bold=True)
txt(179,5,'IPR within ILGS',7,color=green,ha='right')

# Offline preprocessing, the contribution occupies most of the top band.
box(3,11,37,55,'#F4F5F5')
txt(6,15,'a  Multi-view inputs',8,bold=True)
pic(ROOT/'dataset/3dovs/bench/images/00.jpg',6,19,27,18)
pic(ROOT/'dataset/3dovs/bench/images/01.jpg',10,22,27,18)
txt(21.5,42,'RGB views',6.5,ha='center')
maps(8,46,26,13)
txt(21.5,62,'Original identity labels',6.3,ha='center')
arrow(40,38,45,38)
box(45,11,135,55,'#EEF7F2',green)
txt(49,15,'b  IPR: offline supervision refinement',8,green,True)
txt(176,15,'Region maps are schematic',5.5,ha='right',color='#63746C')
maps(49,23,23,14,'raw'); arrow(73,30,78,30,green); maps(79,23,23,14,'clean')
txt(76,20,'Local cleanup',7,bold=True,ha='center')
txt(60.5,40,'Input IDs',6,ha='center'); txt(90.5,40,'Cleaned IDs',6,ha='center')
txt(76,45,'Reassign small components',6,ha='center')
txt(76,50,'No new identities',6.5,green,True,ha='center')
txt(76,58,r'Base confidence $c_t^0(x)$',7,ha='center')
arrow(105,30,111,30,green)
txt(115,21,'Object reliability',7,bold=True)
txt(115,29,'Large-region risk',6.8)
txt(174,29,r'$g_i$',8,ha='right')
txt(115,36,'Else: crop semantic vote',6.8)
txt(174,36,r'$q_i, m_i$',8,ha='right')
txt(115,42,'OpenCLIP + candidate vocabulary',5.8,color='#56676A')
arrow(147,45,147,49,green)
txt(147,53,r'$s_i \in \{0.35,\ 0.65,\ 1\}$',8,green,ha='center')
txt(147,60,r'$s_i \rightarrow h_t(x)$  (pixel assignment)',6.5,ha='center')
txt(76,63,r'$w_t=\mathrm{clip}(c_t^0 h_t,\,0.05,\,1)$',6.5,ha='center')

# Training branch: two separate outputs make label/weight distinction explicit.
arrow(76,66,76,71,green)
box(3,71,177,35,'#EDF3F9',blue)
txt(7,76,'c  Confidence-weighted ILGS training',8,blue,True)
maps(8,81,19,13,'clean'); maps(33,81,19,13,'confidence')
txt(17.5,98,r'$\widetilde{Y}_t$',8,ha='center')
txt(42.5,98,r'$w_t(x)$',8,ha='center')
arrow(54,88,64,88,green)
txt(87,85,'Weighted identity loss',7,bold=True,ha='center')
txt(87,93,r'$\frac{\sum_x o_t(x)w_t(x)\ell_t(x)}{\log C\,\max\{\sum_x o_t(x)w_t(x),\,1\}}$',8.4,ha='center')
arrow(112,88,121,88,blue)
for k in range(12):
    x=126+(k%4)*4; y=83+(k//4)*4
    ax.add_patch(Ellipse((x,y),5,2.4,angle=(k*31)%170,fc=['#4393C3','#F1A340','#5AAE61'][k%3],alpha=.65,ec='white',lw=.4))
txt(159,86,'Language + identity\n3D Gaussian field',7,bold=True,ha='center')
txt(119,102,'RGB, language and 3D consistency losses retained',5.8,ha='center',color='#546371')

# Query path is inherited; there is no fabricated expansion sequence.
arrow(159,106,159,111,blue)
box(3,111,177,36,'#F4F6FB',blue)
txt(7,116,'d  Shared ILGS query pipeline',8,blue,True)
txt(7,123,'Rasterized language\nand identity features',6.5)
arrow(37,127,43,127,blue)
txt(57,123,'Text query',6.5,bold=True,ha='center')
txt(57,130,'Segment similarity\n+ seed selection',6.2,ha='center')
arrow(72,127,78,127,blue)
txt(90,126,'Progressive\nmask expansion',6.5,bold=True,ha='center')
arrow(104,127,112,127,blue)
# Real predictions are panel crops with no pixel modifications.
plate=Image.open(r'D:/downloads/seed0_cases_v2/fig_3dovs_recovery.png')
sw,sh=plate.size
for name,x0,x1,x in [('baseline',1135/1998,1544/1998,115),('ipr',1557/1998,1964/1998,149)]:
    crop=plate.crop((round(x0*sw),round(109/1248*sh),round(x1*sw),round(414/1248*sh)))
    path=OUT/f'bench_{name}_real.png'; crop.save(path)
    pic(path,x,122,27,20)
txt(128.5,144,'Controlled ILGS',5.8,ha='center')
txt(162.5,144,'IPR',5.8,green,True,ha='center')
txt(4,151,'Real endpoint example: Bench / Portuguese egg tart / seed 0.  Intermediate region maps: schematic.',5.8)

def save_cns_figure(fig, filename):
    fig.savefig(f'{filename}.pdf',bbox_inches='tight',dpi=300)
    fig.savefig(f'{filename}.png',bbox_inches='tight',dpi=300)

fig.savefig(OUT/'IPR_method_overview.svg',dpi=300)
fig.savefig(OUT/'IPR_method_overview.pdf',dpi=300)
fig.savefig(OUT/'IPR_method_overview.png',dpi=600)
fig.savefig(OUT/'IPR_method_preview.png',dpi=200)
manifest={
    'figure':'Schematic-led method overview, 183 x 155 mm nominal canvas',
    'rgb':'dataset/3dovs/bench/images/00.jpg and 01.jpg',
    'predictions':'D:/downloads/seed0_cases_v2/fig_3dovs_recovery.png; first row, prediction panels, cropped without changing pixels',
    'schematic':['identity regions','confidence regions','Gaussian ellipses'],
    'not_measured':['No real confidence map available locally','No actual seed/expansion sequence displayed'],
    'ai_generated_images':False,
}
(OUT/'asset_provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# IPR method figure

English labels; SVG text/arrows are editable. PDF contains vector labels with embedded raster photographs. PNG is 600 dpi.

The actual query endpoints come from the previously exported Bench seed-0 comparison plate. These images include white GT boundary outlines inherited from that plate. They are explanatory examples, not an additional experiment.

Colored region maps and Gaussian ellipses are explicitly schematic. They are not measured masks, confidence values or trained Gaussians. The figure does not show fabricated expansion intermediate states.

For a fully empirical replacement, export matching Bench files from the server: original object_mask, object_mask_refined, object_confidence_refined, object_confidence_ipr; object_semantics.json and object_semantic_crops.csv; rasterized language/identity features; actual seed and expansion states from the common seed_ref decoder. Do not use ground-truth masks as pseudo-labels.

Caption: Overview of IPR within ILGS. Multi-view identity labels undergo local cleanup within the existing identity vocabulary. A priority rule combines large-region risk with crop-based semantic evidence to assign object reliability, which modulates base pixel confidence for identity supervision. Language Gaussian training and the shared query decoder produce text-conditioned masks. Region maps are schematic; endpoint images show a real Bench seed-0 example.
''',encoding='utf-8')
print(OUT)
