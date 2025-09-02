# demo_agent.py - Simple launcher for the autonomous SmartMirrorAgent
"""
Autonomous SmartMirrorAgent - Just enter a website, agent does the rest!

Features:
- Intelligent site reconnaissance 
- Automatic strategy selection
- Smart coverage targeting (90% of important content)
- Quality-driven stopping
- Static mirror generation
"""

import asyncio
import sys
from run_agent import run_agent_interactive

def main():
    print(" SmartMirrorAgent - Autonomous Demo Site Builder")
    print("Just enter a website URL - the AI agent handles everything else!")
    print("-" * 60)
    
    try:
        asyncio.run(run_agent_interactive())
    except KeyboardInterrupt:
        print("\n Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()