#!/usr/bin/env python3
"""
Hotspot Analysis - Identifies files that are both complex and frequently changed.

Based on "Your Code as a Crime Scene" by Adam Tornhill:
- Hotspots = High Complexity (LOC) + High Change Frequency (Revisions)
- These are the highest risk areas for bugs and maintenance issues
"""

import os
import subprocess
import csv
from collections import defaultdict
from pathlib import Path


def get_lines_of_code(file_path):
    """Count lines of code in a file"""
    if not os.path.exists(file_path):
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith('#'))
    except:
        return 0


def parse_revisions_csv(csv_data):
    """Parse code-maat revisions output"""
    lines = csv_data.strip().split('\n')
    reader = csv.DictReader(lines)
    return {row['entity']: int(row['n-revs']) for row in reader}


def parse_churn_csv(csv_data):
    """Parse code-maat entity-churn output"""
    lines = csv_data.strip().split('\n')
    reader = csv.DictReader(lines)
    result = {}
    for row in reader:
        result[row['entity']] = {
            'added': int(row['added']),
            'deleted': int(row['deleted']),
            'commits': int(row['commits'])
        }
    return result


def normalize(value, min_val, max_val):
    """Normalize a value to 0-1 range"""
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def calculate_hotspot_score(loc, revisions, max_loc, max_revs):
    """
    Calculate hotspot score (0-100)

    Hotspot = Complexity × Change Frequency
    - Higher LOC = Higher complexity
    - Higher revisions = Higher instability/risk
    """
    if max_loc == 0 or max_revs == 0:
        return 0.0

    # Normalize both metrics to 0-1
    complexity = normalize(loc, 0, max_loc)
    change_freq = normalize(revisions, 0, max_revs)

    # Hotspot score is the product (both high = highest score)
    return complexity * change_freq * 100


def main():
    """Main hotspot analysis"""
    repo_root = "/home/anak/dev/dr-daily-report"
    os.chdir(repo_root)

    print("🔥 HOTSPOT ANALYSIS")
    print("=" * 80)
    print("Identifying files that combine high complexity with high change frequency")
    print()

    # Run code-maat analyses
    print("📊 Running code-maat analyses...")

    # Get revisions data
    result = subprocess.run(
        ['java', '-jar', '/tmp/code-maat.jar', '-l', '/tmp/git-log.txt', '-c', 'git2', '-a', 'revisions'],
        capture_output=True,
        text=True
    )
    revisions = parse_revisions_csv(result.stdout)

    # Get churn data
    result = subprocess.run(
        ['java', '-jar', '/tmp/code-maat.jar', '-l', '/tmp/git-log.txt', '-c', 'git2', '-a', 'entity-churn'],
        capture_output=True,
        text=True
    )
    churn_data = parse_churn_csv(result.stdout)

    # Collect data for all source files
    hotspot_data = []

    for file_path in revisions.keys():
        # Only analyze source files, not tests
        if not file_path.startswith('src/') or file_path.endswith('__init__.py'):
            continue

        full_path = os.path.join(repo_root, file_path)
        loc = get_lines_of_code(full_path)
        n_revs = revisions.get(file_path, 0)
        churn = churn_data.get(file_path, {})

        hotspot_data.append({
            'file': file_path,
            'loc': loc,
            'revisions': n_revs,
            'added': churn.get('added', 0),
            'deleted': churn.get('deleted', 0),
            'total_churn': churn.get('added', 0) + churn.get('deleted', 0)
        })

    # Calculate max values for normalization
    max_loc = max(d['loc'] for d in hotspot_data) if hotspot_data else 1
    max_revs = max(d['revisions'] for d in hotspot_data) if hotspot_data else 1

    # Calculate hotspot scores
    for item in hotspot_data:
        item['hotspot_score'] = calculate_hotspot_score(
            item['loc'],
            item['revisions'],
            max_loc,
            max_revs
        )

    # Sort by hotspot score
    hotspot_data.sort(key=lambda x: x['hotspot_score'], reverse=True)

    # Print results
    print("\n🔥 HOTSPOT RANKING (Top 15)")
    print("=" * 120)
    print(f"{'File':<40} {'LOC':>6} {'Revs':>6} {'Churn':>8} {'Hotspot':>10}  {'Risk Level':<15}")
    print("-" * 120)

    for i, item in enumerate(hotspot_data[:15], 1):
        score = item['hotspot_score']

        # Risk levels
        if score >= 40:
            risk = "🔴 CRITICAL"
        elif score >= 25:
            risk = "🟠 HIGH"
        elif score >= 10:
            risk = "🟡 MEDIUM"
        else:
            risk = "🟢 LOW"

        filename = item['file'].replace('src/', '')
        print(f"{filename:<40} {item['loc']:>6} {item['revisions']:>6} {item['total_churn']:>8} {score:>9.1f}  {risk:<15}")

    # Summary statistics
    print("\n\n📈 SUMMARY STATISTICS")
    print("=" * 80)

    critical = sum(1 for x in hotspot_data if x['hotspot_score'] >= 40)
    high = sum(1 for x in hotspot_data if 25 <= x['hotspot_score'] < 40)
    medium = sum(1 for x in hotspot_data if 10 <= x['hotspot_score'] < 25)
    low = sum(1 for x in hotspot_data if x['hotspot_score'] < 10)

    print(f"Total source files analyzed: {len(hotspot_data)}")
    print(f"🔴 Critical hotspots (score ≥ 40):  {critical}")
    print(f"🟠 High risk (25-40):                {high}")
    print(f"🟡 Medium risk (10-25):              {medium}")
    print(f"🟢 Low risk (< 10):                  {low}")

    # Top offenders
    print("\n\n⚠️  DETAILED ANALYSIS - TOP 3 HOTSPOTS")
    print("=" * 80)

    for item in hotspot_data[:3]:
        filename = item['file'].replace('src/', '')
        print(f"\n📁 {filename}")
        print(f"   Lines of Code:    {item['loc']:,}")
        print(f"   Revisions:        {item['revisions']}")
        print(f"   Code Added:       {item['added']:,}")
        print(f"   Code Deleted:     {item['deleted']:,}")
        print(f"   Total Churn:      {item['total_churn']:,}")
        print(f"   Hotspot Score:    {item['hotspot_score']:.1f}/100")

        if item['hotspot_score'] >= 40:
            print(f"   ⚠️  RECOMMENDATION: This file needs immediate attention!")
            print(f"       - Consider breaking it into smaller modules")
            print(f"       - Extract complex logic into separate files")
            print(f"       - Add comprehensive tests to prevent regressions")

    print("\n\n💡 INTERPRETATION")
    print("=" * 80)
    print("Hotspots are files that combine high complexity (LOC) with high change")
    print("frequency (revisions). These are the riskiest parts of your codebase:")
    print()
    print("• High LOC + High Revisions = 🔴 Critical hotspot (refactor urgently)")
    print("• High LOC + Low Revisions  = Stable complexity (monitor)")
    print("• Low LOC + High Revisions  = Unstable but simple (may indicate design issues)")
    print("• Low LOC + Low Revisions   = 🟢 Healthy code")
    print()
    print("Focus refactoring efforts on critical hotspots to reduce technical debt.")
    print()


if __name__ == '__main__':
    main()
