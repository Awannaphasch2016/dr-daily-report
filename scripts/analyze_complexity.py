#!/usr/bin/env python3
"""
Code complexity analysis script using radon
"""
import subprocess
import sys
import os

def install_radon():
    """Install radon if not already installed"""
    try:
        import radon
        print("? radon is already installed")
        return True
    except ImportError:
        print("Installing radon...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "radon", "--quiet"])
            print("? radon installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("? Failed to install radon")
            return False

def analyze_complexity():
    """Run radon complexity analysis"""
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    
    print("\n" + "="*80)
    print("CODE COMPLEXITY ANALYSIS")
    print("="*80)
    print("\nComplexity Ratings:")
    print("  A: Simple (1-5) - Good")
    print("  B: More complex (6-10) - Acceptable")
    print("  C: Complex (11-20) - Refactor recommended")
    print("  D: Very complex (21-30) - Refactor required")
    print("  E: Extremely complex (31+) - Refactor immediately")
    print("\n" + "-"*80)
    
    try:
        # Run radon cc (cyclomatic complexity)
        result = subprocess.run(
            ["radon", "cc", src_dir, "--min", "B", "--show-complexity"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 or result.stdout:
            print(result.stdout)
        
        # Also get detailed report
        print("\n" + "-"*80)
        print("DETAILED COMPLEXITY REPORT (All functions):")
        print("-"*80)
        
        result_detailed = subprocess.run(
            ["radon", "cc", src_dir, "--min", "A"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result_detailed.stdout:
            print(result_detailed.stdout)
        
        # Count functions by complexity
        print("\n" + "-"*80)
        print("COMPLEXITY SUMMARY:")
        print("-"*80)
        
        result_summary = subprocess.run(
            ["radon", "cc", src_dir, "--total-average"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result_summary.stdout:
            print(result_summary.stdout)
            
    except FileNotFoundError:
        print("? radon not found. Please install it: pip install radon")
        return False
    
    return True

if __name__ == "__main__":
    if install_radon():
        analyze_complexity()
    else:
        sys.exit(1)
