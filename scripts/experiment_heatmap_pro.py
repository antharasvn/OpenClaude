#!/usr/bin/env python3
"""
CleanPro Experiment Heatmap - Pro Version
==========================================
Professional design with branding, gradients, and clean typography.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from pathlib import Path
import json
import subprocess
from datetime import datetime

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'reports'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGO_PATH = Path.home() / 'Projects/CleanPro/source/dev/ios/Cleaner/Assets.xcassets/AppIcon.appiconset/cleanpro_logo_colorful.png'

# CleanPro brand colors
COLORS = {
    'bg_dark': '#0a1628',
    'bg_card': '#111d2e',
    'cyan': '#00d4ff',
    'cyan_dark': '#0099cc',
    'orange': '#ff9500',
    'purple': '#af52de',
    'text_primary': '#ffffff',
    'text_secondary': '#8899aa',
    'border': '#1e3a5f',
}

# Metric colors (vibrant scale)
def get_metric_color(value, metric='conv'):
    """Get color based on value - using vibrant scale."""
    if metric == 'conv':
        if value > 30: return '#9b59b6'   # Purple - exceptional
        elif value > 20: return '#3498db' # Blue - excellent
        elif value > 15: return '#2ecc71' # Green - great
        elif value > 10: return '#27ae60' # Dark green - good
        elif value > 5: return '#f39c12'  # Orange - okay
        elif value > 2: return '#e67e22'  # Dark orange - warning
        else: return '#e74c3c'            # Red - poor
    elif metric == 'completion':
        if value >= 90: return '#9b59b6'
        elif value >= 85: return '#3498db'
        elif value >= 80: return '#2ecc71'
        elif value >= 75: return '#27ae60'
        elif value >= 70: return '#f39c12'
        elif value >= 60: return '#e67e22'
        else: return '#e74c3c'
    return '#7f8c8d'


def bq_query(sql: str):
    cp = subprocess.run(
        ['bq', 'query', '--use_legacy_sql=false', '--project_id=cleaner-app-e98f0', '--format=json'],
        input=sql, text=True, capture_output=True, check=False, timeout=600
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return json.loads(cp.stdout or '[]')


def get_running_experiments():
    """Get list of running experiments from Firebase CLI."""
    result = subprocess.run(
        ['firebase', 'remoteconfig:experiments:list', '--project', 'cleaner-app-e98f0', '--pageSize', '0'],
        capture_output=True, text=True, timeout=120
    )
    
    experiments = []
    lines = result.stdout.split('\n')
    for line in lines:
        if '│ RUNNING │' in line:
            parts = [p.strip() for p in line.split('│') if p.strip()]
            if len(parts) >= 6:
                experiments.append({
                    'id': parts[0],
                    'name': parts[1][:30],
                    'start_time': parts[4][:10]
                })
    return experiments


def get_experiment_metrics():
    """Get metrics for all running experiments."""
    experiments = get_running_experiments()
    if not experiments:
        return []
    
    results = []
    exp_name_map = {exp['id']: exp['name'] for exp in experiments}
    
    for exp in experiments[:10]:
        exp_id = exp['id']
        sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` 
  WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` 
  WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))
),
exp_users AS (
  SELECT 
    user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') as variant
  FROM all_events
  WHERE (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') IS NOT NULL
  GROUP BY 1, 2
),
user_events AS (
  SELECT 
    ue.variant,
    e.user_pseudo_id,
    MAX(IF(e.event_name = 'onboarding_paywall_shown', 1, 0)) as saw_paywall,
    MAX(IF(e.event_name IN ('onboarding_paywall_dismissed', 'onboarding_paywall_converted'), 1, 0)) as finished,
    MAX(IF(e.event_name = 'rc_trial_start', 1, 0)) as trial,
    MAX(IF(e.event_name IN ('onboarding_paywall_converted', 'rc_initial_purchase'), 1, 0)) as converted
  FROM all_events e
  JOIN exp_users ue ON e.user_pseudo_id = ue.user_pseudo_id
  WHERE e.event_timestamp >= UNIX_MICROS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR))
  GROUP BY 1, 2
)
SELECT 
  variant,
  SUM(saw_paywall) as users,
  ROUND(SAFE_DIVIDE(SUM(finished), SUM(saw_paywall)) * 100, 1) as completion,
  ROUND(SAFE_DIVIDE(SUM(trial), SUM(saw_paywall)) * 100, 1) as trial_rate,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall)) * 100, 1) as conv_rate
FROM user_events
WHERE saw_paywall = 1
GROUP BY variant
ORDER BY variant
'''
        try:
            rows = bq_query(sql)
            for row in rows:
                row['exp_id'] = exp_id
                row['exp_name'] = exp_name_map.get(exp_id, exp_id)
            results.extend(rows)
        except Exception as e:
            print(f"Error for exp {exp_id}: {e}")
    
    return results


def create_heatmap(metrics, output_path):
    """Create professional experiment heatmap."""
    if not metrics:
        print("No metrics to display")
        return None
    
    # Group by experiment
    exp_data = {}
    for row in metrics:
        exp_id = row.get('exp_id', '?')
        if exp_id not in exp_data:
            exp_data[exp_id] = {'name': row.get('exp_name', exp_id), 'variants': {}}
        variant = row.get('variant', '0')
        exp_data[exp_id]['variants'][variant] = {
            'users': int(row.get('users', 0) or 0),
            'completion': float(row.get('completion', 0) or 0),
            'trial': float(row.get('trial_rate', 0) or 0),
            'conv': float(row.get('conv_rate', 0) or 0)
        }
    
    # Build rows
    rows = []
    for exp_id, data in sorted(exp_data.items(), key=lambda x: int(x[0])):
        for variant in sorted(data['variants'].keys()):
            rows.append((exp_id, data['name'], variant, data['variants'][variant]))
    
    # Setup figure
    n_rows = len(rows)
    fig_height = max(5, n_rows * 0.45 + 2.5)
    fig, ax = plt.subplots(figsize=(11, fig_height), facecolor=COLORS['bg_dark'])
    ax.set_facecolor(COLORS['bg_dark'])
    
    # Add logo
    if LOGO_PATH.exists():
        try:
            logo = mpimg.imread(str(LOGO_PATH))
            imagebox = OffsetImage(logo, zoom=0.04)
            ab = AnnotationBbox(imagebox, (0.06, 0.96), frameon=False, 
                              xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab)
        except Exception as e:
            print(f"Logo error: {e}")
    
    # Title
    now = datetime.now()
    ax.text(0.12, 0.96, 'CleanPro', ha='left', va='center',
            fontsize=18, fontweight='bold', color=COLORS['cyan'],
            transform=ax.transAxes, family='sans-serif')
    ax.text(0.26, 0.96, 'Experiments', ha='left', va='center',
            fontsize=18, fontweight='normal', color=COLORS['text_primary'],
            transform=ax.transAxes, family='sans-serif')
    
    # Subtitle with timestamp
    ax.text(0.12, 0.91, f"Rolling 24h • {now.strftime('%Y-%m-%d %H:%M')} ICT", 
            ha='left', va='center', fontsize=10, color=COLORS['text_secondary'],
            transform=ax.transAxes)
    
    # Separator line
    ax.axhline(y=0.87, color=COLORS['border'], linewidth=1, xmin=0.04, xmax=0.96)
    
    # Column headers
    cols = ['EXPERIMENT', 'USERS', 'DONE', 'TRIAL', 'CONV']
    col_x = [0.14, 0.38, 0.52, 0.68, 0.84]
    
    for i, col in enumerate(cols):
        ax.text(col_x[i], 0.83, col, ha='center', va='center', 
                fontsize=9, fontweight='bold', color=COLORS['text_secondary'],
                transform=ax.transAxes, family='sans-serif')
    
    # Calculate row positions
    row_height = 0.72 / max(n_rows, 1)
    start_y = 0.78
    
    for idx, (exp_id, exp_name, variant, vals) in enumerate(rows):
        y = start_y - idx * row_height
        
        # Alternate row background
        if idx % 2 == 0:
            rect = FancyBboxPatch((0.04, y - row_height/2 + 0.01), 0.92, row_height - 0.01,
                                  boxstyle="round,pad=0.005", 
                                  facecolor=COLORS['bg_card'], edgecolor='none',
                                  transform=ax.transAxes)
            ax.add_patch(rect)
        
        # Experiment label: "Exp 49 B" or "Exp 49 V1"
        var_label = 'B' if variant == '0' else f'V{variant}'
        display_name = f"Exp {exp_id} {var_label}"
        
        # Highlight baseline vs variant
        name_color = COLORS['cyan'] if variant == '0' else COLORS['orange']
        ax.text(col_x[0], y, display_name, ha='center', va='center', 
                fontsize=11, fontweight='bold', color=name_color,
                transform=ax.transAxes)
        
        # Users
        ax.text(col_x[1], y, str(vals['users']), ha='center', va='center', 
                fontsize=11, color=COLORS['text_primary'],
                transform=ax.transAxes)
        
        # Metric pills
        metrics_data = [
            (col_x[2], vals['completion'], 'completion'),
            (col_x[3], vals['trial'], 'conv'),
            (col_x[4], vals['conv'], 'conv'),
        ]
        
        for x, value, metric_type in metrics_data:
            color = get_metric_color(value, metric_type)
            
            # Pill background
            pill_width = 0.10
            pill_height = row_height * 0.7
            rect = FancyBboxPatch((x - pill_width/2, y - pill_height/2), 
                                  pill_width, pill_height,
                                  boxstyle="round,pad=0.008,rounding_size=0.015", 
                                  facecolor=color, edgecolor='none',
                                  transform=ax.transAxes)
            ax.add_patch(rect)
            
            # Value text
            ax.text(x, y, f"{value:.0f}%", ha='center', va='center', 
                    fontsize=10, fontweight='bold', color='white',
                    transform=ax.transAxes)
    
    # Legend at bottom
    legend_y = 0.03
    legend_items = [
        ('#9b59b6', '>30%'), ('#3498db', '>20%'), ('#2ecc71', '>15%'),
        ('#27ae60', '>10%'), ('#f39c12', '>5%'), ('#e67e22', '>2%'), ('#e74c3c', '≤2%')
    ]
    
    ax.text(0.04, legend_y, 'CONVERSION:', ha='left', va='center',
            fontsize=8, color=COLORS['text_secondary'], transform=ax.transAxes)
    
    legend_x_start = 0.18
    for i, (color, label) in enumerate(legend_items):
        x = legend_x_start + i * 0.11
        rect = FancyBboxPatch((x - 0.015, legend_y - 0.012), 0.03, 0.024,
                              boxstyle="round,pad=0.003",
                              facecolor=color, edgecolor='none',
                              transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x + 0.025, legend_y, label, ha='left', va='center', 
                fontsize=8, color=COLORS['text_secondary'], transform=ax.transAxes)
    
    # Branding footer
    ax.text(0.96, legend_y, 'AAAI Studio', ha='right', va='center',
            fontsize=8, fontweight='bold', color=COLORS['text_secondary'],
            transform=ax.transAxes, alpha=0.6)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    plt.tight_layout(pad=0.5)
    plt.savefig(output_path, dpi=180, facecolor=COLORS['bg_dark'], 
                bbox_inches='tight', pad_inches=0.15)
    plt.close()
    
    print(f"Saved: {output_path}")
    return output_path


def main():
    print("Fetching experiment metrics...")
    metrics = get_experiment_metrics()
    print(f"Got {len(metrics)} rows")
    
    output_path = OUTPUT_DIR / 'experiments_heatmap_pro.png'
    create_heatmap(metrics, output_path)
    
    return str(output_path)


if __name__ == '__main__':
    main()
