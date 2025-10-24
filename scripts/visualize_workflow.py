#!/usr/bin/env python3
"""Generate visual diagram of OEWS workflow graph."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import sys


def create_workflow_diagram(output_path="docs/workflow-diagram.png"):
    """
    Create a visual diagram of the OEWS workflow.

    Args:
        output_path: Where to save the diagram
    """
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Define node positions (x, y)
    positions = {
        'START': (7, 9),
        'planner': (7, 7.5),
        'executor': (7, 5.5),
        'cortex_researcher': (2, 3.5),
        'web_researcher': (5, 3.5),
        'chart_generator': (8, 3.5),
        'synthesizer': (11, 3.5),
        'chart_summarizer': (8, 2),
        'response_formatter': (7, 0.5),
        'END': (7, -0.5),
    }

    # Define node styles
    node_styles = {
        'START': {'color': '#e1f5e1', 'shape': 'round'},
        'END': {'color': '#ffe1e1', 'shape': 'round'},
        'planner': {'color': '#e3f2fd', 'shape': 'box'},
        'executor': {'color': '#fff3e0', 'shape': 'diamond'},
        'cortex_researcher': {'color': '#f3e5f5', 'shape': 'box'},
        'web_researcher': {'color': '#f3e5f5', 'shape': 'box'},
        'chart_generator': {'color': '#f3e5f5', 'shape': 'box'},
        'synthesizer': {'color': '#f3e5f5', 'shape': 'box'},
        'chart_summarizer': {'color': '#f3e5f5', 'shape': 'box'},
        'response_formatter': {'color': '#e8f5e9', 'shape': 'box'},
    }

    # Define node labels
    node_labels = {
        'START': 'START',
        'planner': 'Planner\n(DeepSeek-R1)\nCreate Plan',
        'executor': 'Executor\nRoute & Control',
        'cortex_researcher': 'Cortex Researcher\n(Text2SQL)\nQuery OEWS DB',
        'web_researcher': 'Web Researcher\n(Tavily)\nWeb Search',
        'chart_generator': 'Chart Generator\nCreate Charts',
        'synthesizer': 'Synthesizer\nText Summary',
        'chart_summarizer': 'Chart Summarizer\nGenerate Caption',
        'response_formatter': 'Response Formatter\nStructured Output',
        'END': 'END',
    }

    # Draw nodes
    for node, (x, y) in positions.items():
        style = node_styles[node]
        label = node_labels[node]

        if style['shape'] == 'diamond':
            # Diamond shape for executor
            diamond = mpatches.FancyBboxPatch(
                (x - 0.7, y - 0.4), 1.4, 0.8,
                boxstyle="round,pad=0.1",
                facecolor=style['color'],
                edgecolor='black',
                linewidth=2
            )
            ax.add_patch(diamond)
        elif style['shape'] == 'round':
            # Rounded rectangle for START/END
            rect = FancyBboxPatch(
                (x - 0.6, y - 0.3), 1.2, 0.6,
                boxstyle="round,pad=0.15",
                facecolor=style['color'],
                edgecolor='black',
                linewidth=2
            )
            ax.add_patch(rect)
        else:
            # Regular box
            rect = FancyBboxPatch(
                (x - 0.7, y - 0.4), 1.4, 0.8,
                boxstyle="round,pad=0.05",
                facecolor=style['color'],
                edgecolor='black',
                linewidth=1.5
            )
            ax.add_patch(rect)

        # Add label
        ax.text(x, y, label, ha='center', va='center',
                fontsize=8, weight='bold', wrap=True)

    # Define edges with labels
    edges = [
        ('START', 'planner', ''),
        ('planner', 'executor', 'initial plan'),
        ('executor', 'planner', 'replan', 'curved'),
        ('executor', 'cortex_researcher', 'route'),
        ('executor', 'web_researcher', 'route'),
        ('executor', 'chart_generator', 'route'),
        ('executor', 'synthesizer', 'route'),
        ('cortex_researcher', 'executor', 'results'),
        ('web_researcher', 'executor', 'results'),
        ('chart_generator', 'chart_summarizer', ''),
        ('chart_summarizer', 'executor', 'caption'),
        ('synthesizer', 'executor', 'summary'),
        ('executor', 'response_formatter', 'complete'),
        ('response_formatter', 'END', ''),
    ]

    # Draw edges
    for edge in edges:
        if len(edge) == 3:
            source, target, label = edge
            curved = False
        else:
            source, target, label, curved = edge[0], edge[1], edge[2], True

        x1, y1 = positions[source]
        x2, y2 = positions[target]

        # Adjust start/end points to edge of boxes
        if source != 'START' and source != 'END':
            if x2 < x1:  # target is to the left
                x1 -= 0.7
            elif x2 > x1:  # target is to the right
                x1 += 0.7
            if y2 < y1:  # target is below
                y1 -= 0.4
            elif y2 > y1:  # target is above
                y1 += 0.4

        if target != 'START' and target != 'END':
            if x1 < x2:  # source is to the left
                x2 -= 0.7
            elif x1 > x2:  # source is to the right
                x2 += 0.7
            if y1 < y2:  # source is below
                y2 -= 0.4
            elif y1 > y2:  # source is above
                y2 += 0.4

        # Draw arrow
        if curved and source == 'executor' and target == 'planner':
            # Curved arrow for replan
            arrow = FancyArrowPatch(
                (x1 - 0.5, y1 + 0.3), (x2 - 0.5, y2 - 0.3),
                connectionstyle="arc3,rad=0.5",
                arrowstyle='->,head_width=0.4,head_length=0.4',
                color='red',
                linewidth=1.5,
                linestyle='--'
            )
        else:
            arrow = FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle='->,head_width=0.4,head_length=0.4',
                color='black',
                linewidth=1.5
            )
        ax.add_patch(arrow)

        # Add edge label
        if label:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y, label, ha='center', va='bottom',
                    fontsize=7, style='italic', color='gray',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Add title
    ax.text(7, 9.8, 'OEWS Data Agent Workflow', ha='center', va='top',
            fontsize=16, weight='bold')

    # Add legend
    legend_elements = [
        mpatches.Patch(facecolor='#e3f2fd', edgecolor='black', label='Control Nodes'),
        mpatches.Patch(facecolor='#f3e5f5', edgecolor='black', label='Agent Nodes'),
        mpatches.Patch(facecolor='#e8f5e9', edgecolor='black', label='Output Nodes'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

    # Save figure
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Workflow diagram saved to: {output_path}")

    return output_path


def main():
    """Main entry point."""
    output = "docs/workflow-diagram.png"
    if len(sys.argv) > 1:
        output = sys.argv[1]

    create_workflow_diagram(output)


if __name__ == "__main__":
    main()
