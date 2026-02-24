#!/usr/bin/env python3
"""
BPMN-like pipeline diagram v3 — wider, no overlaps.
Swim lanes: Manual | Scripts | Tools | Data
5 phases left-to-right.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(1, 1, figsize=(24, 13))
ax.set_xlim(0, 24)
ax.set_ylim(0, 13)
ax.axis('off')

# ============================================================
# COLORS
# ============================================================
C_MANUAL  = '#F9E79F'
C_SCRIPT  = '#85C1E9'
C_TOOL    = '#82E0AA'
C_DATA    = '#D2B4DE'
C_RQ      = '#F1948A'
C_BORDER  = '#2C3E50'
C_TEXT    = '#1B2631'
C_ARROW   = '#566573'

# Lane Y positions (center of each lane)
Y_MANUAL = 10.5
Y_SCRIPT = 8.0
Y_TOOL   = 5.5
Y_DATA   = 3.0

# ============================================================
# HELPERS
# ============================================================
def box(x, y, w, h, text, color, fontsize=7.5, bold=False, lw=1.2):
    b = FancyBboxPatch((x - w/2, y - h/2), w, h,
                        boxstyle="round,pad=0.1", facecolor=color,
                        edgecolor=C_BORDER, linewidth=lw, zorder=3)
    ax.add_patch(b)
    fw = 'bold' if bold else 'normal'
    ax.text(x, y, text, fontsize=fontsize, ha='center', va='center',
            color=C_TEXT, fontweight=fw, linespacing=1.35, zorder=4)

def arr(x1, y1, x2, y2, label=None, lbl_offset=(0, 0.18), fontsize=6.5, color=C_ARROW, lw=1.3):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=2)
    if label:
        mx = (x1+x2)/2 + lbl_offset[0]
        my = (y1+y2)/2 + lbl_offset[1]
        ax.text(mx, my, label, fontsize=fontsize, color=color,
                ha='center', va='bottom', fontstyle='italic', zorder=5)

def arr_curved(x1, y1, x2, y2, label=None, rad=0.3, color=C_ARROW, fontsize=6):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.2,
                               connectionstyle=f"arc3,rad={rad}"), zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2 + 0.3
        ax.text(mx, my, label, fontsize=fontsize, color=color,
                ha='center', fontstyle='italic', zorder=5)

# ============================================================
# TITLE
# ============================================================
ax.text(12, 12.55, 'Processo Metodológico', fontsize=16, fontweight='bold',
        ha='center', color=C_TEXT)
ax.text(12, 12.1, 'Pipeline de Coleta, Detecção, Consolidação e Análise',
        fontsize=11, ha='center', color='#5D6D7E')

# ============================================================
# LANE BACKGROUNDS (light horizontal bands)
# ============================================================
lane_bands = [
    (Y_MANUAL, '#FFF8E7', 'Pesquisador\n(manual)'),
    (Y_SCRIPT, '#EBF5FB', 'Scripts\n(automatizado)'),
    (Y_TOOL,   '#E8F8F5', 'Ferramentas\nexternas'),
    (Y_DATA,   '#F5EEF8', 'Dados\n(entrada/saída)'),
]

for yc, bg_color, label in lane_bands:
    rect = FancyBboxPatch((2.6, yc - 1.1), 21.0, 2.2,
                           boxstyle="round,pad=0.05", facecolor=bg_color,
                           edgecolor='#D5D8DC', linewidth=0.6, alpha=0.35, zorder=0)
    ax.add_patch(rect)
    ax.text(1.3, yc, label, fontsize=8, fontweight='bold',
            ha='center', va='center', color=C_BORDER, linespacing=1.3, zorder=1)

# ============================================================
# PHASE SEPARATORS (vertical dashed lines) + labels
# ============================================================
phase_seps = [5.8, 9.2, 12.5, 16.0]
for x_sep in phase_seps:
    ax.plot([x_sep, x_sep], [1.5, 11.7], color='#D5D8DC', linestyle='--',
            linewidth=0.7, zorder=0)

for x, label in [(4.2, 'Fase 1\nColeta'), (7.5, 'Fase 2\nDetecção'),
                  (10.8, 'Fase 3\nConsolidação'), (14.2, 'Fase 4\nAnálise'),
                  (20.0, 'Fase 5\nTemporal')]:
    ax.text(x, 11.7, label, fontsize=8.5, fontweight='bold', ha='center',
            color='#7F8C8D', zorder=1, linespacing=1.2)

# ============================================================
# FASE 1: COLETA (x ~ 3-5.5)
# ============================================================
box(3.5, Y_MANUAL, 2.0, 0.9, 'Definição de\ncritérios IC/EC', C_MANUAL, bold=True, fontsize=7.5)

box(3.5, Y_SCRIPT, 2.0, 0.9, '02_expand_dataset.sh\n05_filter_dataset.py', C_SCRIPT, fontsize=7)

box(4.2, Y_DATA, 2.0, 0.8, '343 candidatos\n→ 318 filtrados', C_DATA, fontsize=7)

arr(3.5, Y_MANUAL - 0.45, 3.5, Y_SCRIPT + 0.45, 'define critérios')
arr(3.5, Y_SCRIPT - 0.45, 4.0, Y_DATA + 0.4, 'gera dataset')

# ============================================================
# FASE 2: DETECÇÃO (x ~ 6.5-9)
# ============================================================
box(7.0, Y_MANUAL, 1.8, 0.9, 'Configurar\ntokens GitHub\ne ambiente', C_MANUAL, fontsize=7)

box(7.0, Y_SCRIPT, 2.0, 0.9, '03_run_pipeline.sh\n(orquestra)', C_SCRIPT, fontsize=7)

box(7.0, Y_TOOL + 0.55, 2.0, 0.7, 'Designite Java\n(Code Smells)', C_TOOL, fontsize=7, bold=True)
box(7.0, Y_TOOL - 0.55, 2.0, 0.7, 'csDetector-fixed\n(Community Smells)', C_TOOL, fontsize=7, bold=True)

box(8.5, Y_DATA, 2.0, 0.8, 'CSVs brutos\n(318 × smells)\n(300 × social)', C_DATA, fontsize=6.5)

# Arrows fase 2
arr(5.2, Y_DATA, 7.5, Y_DATA)                          # data right
arr(4.5, Y_SCRIPT, 6.0, Y_SCRIPT)                      # script right
arr(7.0, Y_MANUAL - 0.45, 7.0, Y_SCRIPT + 0.45, 'executa')
arr(7.0, Y_SCRIPT - 0.45, 7.0, Y_TOOL + 0.9, 'invoca')
arr(7.0, Y_TOOL + 0.2, 7.0, Y_TOOL - 0.2, color='#AAB7B8', lw=0.8)
arr(8.0, Y_TOOL + 0.55, 8.5, Y_DATA + 0.4)
arr(8.0, Y_TOOL - 0.55, 8.5, Y_DATA + 0.4)

# ============================================================
# FASE 3: CONSOLIDAÇÃO (x ~ 10-12)
# ============================================================
box(10.5, Y_SCRIPT, 2.2, 0.9, '04_consolidate.py', C_SCRIPT, fontsize=7)

box(10.5, Y_DATA, 2.2, 0.8, 'consolidated_\nfull_300.csv\n(N = 300)', C_DATA, fontsize=7, bold=True)

# V2 consolidation
box(12.0, Y_SCRIPT - 1.2, 2.2, 0.65, '13_consolidate_\nunified.py (V2)', C_SCRIPT, fontsize=6.5, lw=0.9)

# V2 incremental pipeline
box(12.0, Y_TOOL, 2.2, 0.65, '10_pipeline_\nincremental.sh\n(V2: +52 repos)', C_SCRIPT, fontsize=6, lw=0.9)

# Arrows fase 3
arr(9.5, Y_DATA, 9.4, Y_DATA)
arr(9.5, Y_SCRIPT, 9.4, Y_SCRIPT)
arr(10.5, Y_SCRIPT - 0.45, 10.5, Y_DATA + 0.4, 'consolida')
arr_curved(12.0, Y_TOOL + 0.33, 10.5, Y_SCRIPT - 0.45, rad=0.3, color='#AAB7B8')

# ============================================================
# FASE 4: ANÁLISE (x ~ 13-15.5)
# ============================================================
box(14.0, Y_SCRIPT + 0.85, 2.2, 0.7, '06_analysis_v2.py\n(Spearman, MW)', C_SCRIPT, fontsize=6.5)
box(14.0, Y_SCRIPT, 2.2, 0.7, '07_analysis_extra.py\n(scatter, clusters)', C_SCRIPT, fontsize=6.5)
box(14.0, Y_SCRIPT - 0.85, 2.2, 0.7, '12_dissertation_\nanalysis.py\n(figuras finais)', C_SCRIPT, fontsize=6.5)

# RQs
box(15.5, Y_SCRIPT + 0.85, 0.9, 0.5, 'RQ1', C_RQ, fontsize=9, bold=True)
box(15.5, Y_SCRIPT, 0.9, 0.5, 'RQ3', C_RQ, fontsize=9, bold=True)

# Data output
box(14.0, Y_DATA, 2.2, 0.8, 'Figuras, tabelas\ne texto da\ndissertação', C_DATA, fontsize=7)

# Arrows fase 4
arr(11.6, Y_DATA, 12.9, Y_DATA)
arr(11.6, Y_SCRIPT, 12.9, Y_SCRIPT)
arr(15.1, Y_SCRIPT + 0.85, 15.05, Y_SCRIPT + 0.85)
arr(15.1, Y_SCRIPT, 15.05, Y_SCRIPT)
arr(14.0, Y_SCRIPT - 1.2, 14.0, Y_DATA + 0.4, 'gera')

# ============================================================
# FASE 5: TEMPORAL (x ~ 17-23)
# ============================================================
box(17.5, Y_MANUAL, 2.0, 0.9, 'Critério IC4\n≥ 2 project years\n(730 dias)', C_MANUAL, fontsize=7, bold=True)

box(17.5, Y_SCRIPT + 0.5, 2.2, 0.7, '08_temporal_\nextraction.py\n(git checkout)', C_SCRIPT, fontsize=6.5)
box(17.5, Y_SCRIPT - 0.5, 2.2, 0.7, '08b_run_designite_\ntemporal.py', C_SCRIPT, fontsize=6.5)

box(20.5, Y_SCRIPT + 0.5, 2.2, 0.7, '09_temporal_\nanalysis.py\n(Friedman, KW)', C_SCRIPT, fontsize=6.5)
box(20.5, Y_SCRIPT - 0.5, 2.2, 0.7, '11_commit_\nconcentration.py', C_SCRIPT, fontsize=6.5)

box(17.5, Y_TOOL + 0.5, 2.0, 0.7, 'Designite Java\n(por snapshot)', C_TOOL, fontsize=7)
box(17.5, Y_TOOL - 0.5, 2.0, 0.7, 'csDetector-fixed\n(por período)', C_TOOL, fontsize=7)

box(20.5, Y_DATA, 2.2, 0.8, 'temporal_data_\ncomplete.csv\n(800 snapshots)', C_DATA, fontsize=7, bold=True)

box(22.0, Y_SCRIPT + 0.85, 0.9, 0.5, 'RQ2', C_RQ, fontsize=9, bold=True)

# Arrows temporal
arr(17.5, Y_MANUAL - 0.45, 17.5, Y_SCRIPT + 0.85, 'filtra repos')
arr(17.5, Y_SCRIPT + 0.15, 17.5, Y_SCRIPT - 0.15, color='#AAB7B8', lw=0.8)
arr(17.5, Y_SCRIPT - 0.85, 17.5, Y_TOOL + 0.85, 'invoca')
arr(17.5, Y_TOOL + 0.15, 17.5, Y_TOOL - 0.15, color='#AAB7B8', lw=0.8)
arr(18.6, Y_SCRIPT + 0.5, 19.4, Y_SCRIPT + 0.5)
arr(18.6, Y_SCRIPT - 0.5, 19.4, Y_SCRIPT - 0.5)
arr(18.5, Y_TOOL + 0.5, 20.5, Y_DATA + 0.4)
arr(18.5, Y_TOOL - 0.5, 20.5, Y_DATA + 0.4)
arr(20.5, Y_SCRIPT + 0.85, 21.55, Y_SCRIPT + 0.85)
arr(20.5, Y_SCRIPT - 0.85, 20.5, Y_DATA + 0.4, 'gera')

# Connect 318 filtered → temporal (curved arrow across diagram)
arr_curved(5.2, Y_DATA + 0.4, 16.5, Y_MANUAL, label='208 repos com ≥ 2 anos', rad=-0.2, fontsize=6.5)

# ============================================================
# LEGEND (bottom)
# ============================================================
items = [
    (C_MANUAL, 'Etapa manual (pesquisador)'),
    (C_SCRIPT, 'Script automatizado'),
    (C_TOOL,   'Ferramenta externa'),
    (C_DATA,   'Dataset (entrada/saída)'),
    (C_RQ,     'Questão de pesquisa'),
]

for i, (color, label) in enumerate(items):
    bx = 3.0 + i * 4.0
    sq = FancyBboxPatch((bx, 0.85), 0.4, 0.3,
                         boxstyle="round,pad=0.03", facecolor=color,
                         edgecolor=C_BORDER, linewidth=0.6, zorder=3)
    ax.add_patch(sq)
    ax.text(bx + 0.55, 1.0, label, fontsize=7, va='center', color=C_TEXT, zorder=4)

plt.tight_layout(pad=0.3)
plt.savefig('/sessions/sleepy-loving-ride/pipeline_bpmn_v3.pdf',
            format='pdf', dpi=300, bbox_inches='tight')
plt.savefig('/sessions/sleepy-loving-ride/pipeline_bpmn_v3.png',
            format='png', dpi=200, bbox_inches='tight')
print("Generated pipeline_bpmn_v3.pdf and .png")
