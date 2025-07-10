#!/usr/bin/env python3
"""
Build script for Azure CLI Chat Assistant
Compiles TypeScript and optionally starts the server
Updated for website folder structure
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status"""
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def ensure_node_modules():
    """Ensure node modules are installed"""
    website_dir = Path('website')
    if not (website_dir / 'node_modules').exists() or not (website_dir / 'node_modules' / 'typescript').exists():
        print("Installing Node.js dependencies...")
        return run_command('npm install', cwd='website')
    return True

def compile_typescript():
    """Compile TypeScript to JavaScript"""
    print("Compiling TypeScript...")
    
    # Ensure output directory exists
    Path('website/static/dist').mkdir(parents=True, exist_ok=True)
    
    # Run TypeScript compiler from website directory
    return run_command('npx tsc', cwd='website')

def copy_assets():
    """Copy any additional assets if needed"""
    # Ensure the dist directory exists
    Path('website/static/dist').mkdir(parents=True, exist_ok=True)
    
    # Create a simple favicon if it doesn't exist
    favicon_path = Path('website/static/favicon.ico')
    if not favicon_path.exists():
        # Create a simple 16x16 transparent PNG renamed as ICO
        print("Creating default favicon...")
        # For now, just create an empty file to prevent 404 errors
        favicon_path.touch()
    
    return True

def main():
    """Main build process"""
    print("Building Azure CLI Chat Assistant...")
    
    # Check if we should just build or also start
    build_only = '--build-only' in sys.argv
    
    # Check if website directory exists
    if not Path('website').exists():
        print("Error: website directory not found. Please run this script from the project root.")
        return 1
    
    # Step 1: Install dependencies
    if not ensure_node_modules():
        print("Failed to install Node.js dependencies")
        return 1
    
    # Step 2: Compile TypeScript
    if not compile_typescript():
        print("Failed to compile TypeScript")
        return 1
    
    # Step 3: Copy assets
    if not copy_assets():
        print("Failed to copy assets")
        return 1
    
    print("Build completed successfully!")
    print(f"Website files are in: {Path('website').absolute()}")
    
    if not build_only:
        print("Starting the web server...")
        # Import and run the Flask app
        try:
            from website_app import main as run_app
            run_app()
        except ImportError as e:
            print(f"Failed to import website_app: {e}")
            print("Make sure you have installed the Python requirements:")
            print("pip install -r requirements.txt")
            return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 