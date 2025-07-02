#!/usr/bin/env python3
"""
Script name: eba_script_v1.0.py

Purpose: Interactively fetch SLO data from Nobl9 and create Error Budget Adjustment YAMLs.
Supports creating budget adjustments for projects or services with customizable templates.

Dependencies: requests, toml, yaml, subprocess, sloctl CLI
Compatible with: macOS and Linux

Author: Jeremy Cooper
Date Created: 2025-07-02
"""

import os
import sys
import json
import yaml
import toml
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Color definitions for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    NC = '\033[0m'  # No Color

def print_colored(text, color, end="\n"):
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.NC}", end=end)

def check_dependencies():
    """Check if required dependencies are available."""
    missing = []
    
    # Check Python packages
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    try:
        import yaml
    except ImportError:
        missing.append("PyYAML")
    
    try:
        import toml
    except ImportError:
        missing.append("toml")
    
    # Check sloctl CLI
    if not shutil.which("sloctl"):
        print_colored("ERROR: 'sloctl' is not installed or not in PATH.", Colors.RED)
        print_colored("You can install it from https://docs.nobl9.com/sloctl/", Colors.CYAN)
        sys.exit(1)
    
    # Check jq (optional but recommended)
    if not shutil.which("jq"):
        print_colored("WARNING: 'jq' is not installed. JSON parsing may be limited.", Colors.YELLOW)
    
    if missing:
        print_colored("\nMissing required Python packages:", Colors.RED)
        for pkg in missing:
            print_colored(f"  - {pkg}", Colors.RED)
        print_colored("\nYou can install them using:", Colors.CYAN)
        print_colored(f"  pip3 install {' '.join(missing)}", Colors.CYAN)
        sys.exit(1)

def setup_directories():
    """Create necessary directories and template files."""
    eba_files_dir = Path("./ebafiles")
    template_dir = eba_files_dir / "templates"
    blank_template = template_dir / "blank_do_not_delete.yml"
    
    # Create directories
    if not eba_files_dir.exists():
        eba_files_dir.mkdir(parents=True, exist_ok=True)
        template_dir.mkdir(parents=True, exist_ok=True)
        print_colored(f"The directory {eba_files_dir} has been created.", Colors.YELLOW)
        print_colored(f"Please add template files to the {template_dir} directory as you see fit.", Colors.CYAN)
    # Create blank template if it doesn't exist
    if not blank_template.exists():
        print_colored("Creating a sample template file called blank_do_not_delete.yml...", Colors.YELLOW)
        template_content = """## https://docs.nobl9.com/yaml-guide/#budgetadjustment
## https://docs.nobl9.com/features/budget-adjustments/
## https://icalendar.org/rrule-tool.html

apiVersion: n9/v1alpha
kind: BudgetAdjustment
metadata:
  name: <string> # Mandatory
  displayName: <string> # Optional
spec:
  description: <string> # Optional
  ######You should edit the firstEventStart and rrule fields - these are just fillers######
  firstEventStart: <YYYY-MM-DDThh:mm:ssZ> # Mandatory
  rrule: <FREQ=MONTHLY;INTERVAL=1;BYDAY=1TU> # Mandatory
  ######################################################
  filters:
    slos:
"""
        blank_template.write_text(template_content)
    
    return eba_files_dir, template_dir

def get_available_contexts():
    """Fetch and display available Nobl9 contexts."""
    print_colored("Fetching available contexts...", Colors.CYAN)
    
    try:
        result = subprocess.run(
            ["sloctl", "config", "get-contexts"],
            capture_output=True,
            text=True,
            check=True
        )
        raw_contexts = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_colored(f"ERROR: Failed to fetch contexts: {e}", Colors.RED)
        sys.exit(1)
    
    # Parse contexts (remove brackets and split by comma)
    contexts = [ctx.strip() for ctx in raw_contexts.strip('[]').split(',') if ctx.strip()]
    
    if not contexts:
        print_colored("No contexts available. Please configure Nobl9 contexts.", Colors.RED)
        sys.exit(1)
    
    print_colored("Available contexts:", Colors.CYAN)
    for i, context in enumerate(contexts, 1):
        print(f"  [{i}] {context}")
    
    while True:
        try:
            choice = int(input("Select a context by number: "))
            if 1 <= choice <= len(contexts):
                selected_context = contexts[choice - 1]
                break
            # Invalid choice - just continue to reprompt
        except ValueError:
            # Invalid input - just continue to reprompt
            pass
    
    # Switch to selected context
    try:
        subprocess.run(
            ["sloctl", "config", "use-context", selected_context],
            check=True,
            capture_output=True
        )
        print_colored(f"Switched to context: {selected_context}", Colors.GREEN)
        return selected_context
    except subprocess.CalledProcessError as e:
        print_colored(f"ERROR: Failed to switch context: {e}", Colors.RED)
        sys.exit(1)

def fetch_slo_data():
    """Fetch SLO data from Nobl9."""
    print_colored("Fetching SLO data from Nobl9...", Colors.CYAN)
    
    try:
        result = subprocess.run(
            ["sloctl", "get", "slos", "-A", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        slos_json = result.stdout.strip()
        
        # Validate JSON
        slos_data = json.loads(slos_json)
        if not isinstance(slos_data, list):
            print_colored("ERROR: Invalid SLO data format.", Colors.RED)
            sys.exit(1)
        
        print_colored(f"✓ Retrieved {len(slos_data)} SLOs", Colors.GREEN)
        return slos_data
        
    except subprocess.CalledProcessError as e:
        print_colored(f"ERROR: Failed to fetch SLO data: {e}", Colors.RED)
        print_colored("Please check your Nobl9 configuration.", Colors.CYAN)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_colored(f"ERROR: Invalid JSON response: {e}", Colors.RED)
        sys.exit(1)

def get_valid_input(prompt, field_name):
    """Get valid user input without '#' characters."""
    while True:
        value = input(prompt).strip()
        if '#' in value:
            print_colored(f"Invalid {field_name}. '#' characters are not allowed.", Colors.RED)
        elif not value:
            print_colored(f"{field_name} cannot be empty.", Colors.RED)
        else:
            return value

def select_template(template_dir):
    """Let user select a template file."""
    templates = list(template_dir.glob("*"))
    
    if not templates:
        print_colored("No templates found in templates directory.", Colors.RED)
        sys.exit(1)
    
    print_colored("Available templates:", Colors.CYAN)
    for i, template in enumerate(templates, 1):
        print(f"  [{i}] {template.name}")
    
    while True:
        try:
            choice = int(input("Select a template by number: "))
            if 1 <= choice <= len(templates):
                return templates[choice - 1]
            # Invalid choice - just continue to reprompt
        except ValueError:
            # Invalid input - just continue to reprompt
            pass

def create_eba_files(entity_name, entity_type, slo_entries, template_dir):
    """Create Error Budget Adjustment YAML files."""
    # Get user input
    print_colored("Enter the ", Colors.NC, end="")
    print_colored("displayName", Colors.YELLOW, end="")
    print_colored(" for the Budget Adjustment (no '#' allowed): ", Colors.NC, end="")
    display_name = get_valid_input("", "displayName")
    
    print_colored("Enter the ", Colors.NC, end="")
    print_colored("description", Colors.GREEN, end="")
    print_colored(" for the Budget Adjustment (no '#' allowed): ", Colors.NC, end="")
    description = get_valid_input("", "description")
    
    # Select template
    selected_template = select_template(template_dir)
    
    # Create output directory
    current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = Path(f"./ebafiles/run-{current_datetime}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate base name
    base_name = display_name.lower().replace(' ', '-').replace('_', '-')
    base_name = ''.join(c for c in base_name if c.isalnum() or c == '-')
    base_name = base_name.strip('-')
    
    # Process SLOs
    file_index = 1
    slo_count = 0
    total_slos = len(slo_entries)
    
    # Sort SLO entries
    slo_entries.sort()
    
    # Create first file
    file_path = output_dir / f"{base_name}.yml"
    shutil.copy2(selected_template, file_path)
    
    # Read and modify template content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace template placeholders
    content = content.replace("name: <string> # Mandatory", f"name: {base_name} # Mandatory")
    content = content.replace("displayName: <string> # Optional", f"displayName: {display_name} # Optional")
    content = content.replace("description: <string> # Optional", f"description: {description} # Optional")
    
    # Add SLO entries
    slo_lines = []
    for slo_entry in slo_entries:
        slo_name, slo_project = slo_entry.split(":::")
        slo_lines.extend([
            f"      - name: {slo_name} # Mandatory",
            f"        project: {slo_project} # Mandatory"
        ])
        slo_count += 1
        
        # Create new file every 30 SLOs
        if slo_count % 30 == 0 and slo_count < total_slos:
            # Write current file
            with open(file_path, 'w') as f:
                f.write(content)
                f.write('\n'.join(slo_lines))
                f.write('\n')
            
            # Create next file
            file_index += 1
            display_name_suffix = f"{display_name}-{file_index}"
            file_suffix = f"-{file_index}"
            file_path = output_dir / f"{base_name}{file_suffix}.yml"
            
            # Copy template and update content
            shutil.copy2(selected_template, file_path)
            with open(file_path, 'r') as f:
                content = f.read()
            
            content = content.replace("name: <string> # Mandatory", f"name: {base_name}{file_suffix} # Mandatory")
            content = content.replace("displayName: <string> # Optional", f"displayName: {display_name_suffix} # Optional")
            content = content.replace("description: <string> # Optional", f"description: {description} # Optional")
            
            slo_lines = []
    
    # Write final file
    with open(file_path, 'w') as f:
        f.write(content)
        f.write('\n'.join(slo_lines))
        f.write('\n')
    
    # Summary
    print_colored(f"YAML files created in {output_dir}", Colors.GREEN)
    print_colored("Unless you updated the template, you will still need to edit the time and duration in the YAML files.", Colors.YELLOW)
    print_colored("Summary:", Colors.CYAN)
    print(f"  Files created: {file_index}")
    print(f"  Total SLOs included: {total_slos}")
    print(f"  Output folder: {output_dir.absolute()}")

def list_projects(slos_data, template_dir):
    """List projects and create EBA files for selected project."""
    print_colored("\nProjects:", Colors.YELLOW)
    
    # Extract unique projects
    projects = {}
    for slo in slos_data:
        project = slo.get('metadata', {}).get('project')
        if project:
            if project not in projects:
                projects[project] = []
            projects[project].append(slo)
    
    # Display projects with SLO counts
    project_list = list(projects.keys())
    for i, project in enumerate(project_list, 1):
        count = len(projects[project])
        print(f"  [{i}] {project} ({Colors.GREEN}{count}{Colors.NC} SLOs)")
    
    # Get user selection
    while True:
        try:
            choice = int(input("Select a project by number: "))
            if 1 <= choice <= len(project_list):
                selected_project = project_list[choice - 1]
                break
            # Invalid choice - just continue to reprompt
        except ValueError:
            # Invalid input - just continue to reprompt
            pass
    
    print_colored(f"Selected project: {selected_project}", Colors.GREEN)
    
    # Create SLO entries for selected project
    slo_entries = []
    for slo in projects[selected_project]:
        slo_name = slo.get('metadata', {}).get('name')
        slo_project = slo.get('metadata', {}).get('project')
        if slo_name and slo_project:
            slo_entries.append(f"{slo_name}:::{slo_project}")
    
    create_eba_files(selected_project, "project", slo_entries, template_dir)

def list_services(slos_data, template_dir):
    """List services and create EBA files for selected service."""
    print_colored("\nServices:", Colors.YELLOW)
    
    # Extract unique services
    services = {}
    for slo in slos_data:
        service = slo.get('spec', {}).get('service')
        if service:
            if service not in services:
                services[service] = []
            services[service].append(slo)
    
    # Display services with SLO counts
    service_list = list(services.keys())
    for i, service in enumerate(service_list, 1):
        count = len(services[service])
        print(f"  [{i}] {service} ({Colors.GREEN}{count}{Colors.NC} SLOs)")
    
    # Get user selection
    while True:
        try:
            choice = int(input("Select a service by number: "))
            if 1 <= choice <= len(service_list):
                selected_service = service_list[choice - 1]
                break
            # Invalid choice - just continue to reprompt
        except ValueError:
            # Invalid input - just continue to reprompt
            pass
    
    print_colored(f"Selected service: {selected_service}", Colors.GREEN)
    
    # Create SLO entries for selected service
    slo_entries = []
    for slo in services[selected_service]:
        slo_name = slo.get('metadata', {}).get('name')
        slo_project = slo.get('metadata', {}).get('project')
        if slo_name and slo_project:
            slo_entries.append(f"{slo_name}:::{slo_project}")
    
    create_eba_files(selected_service, "service", slo_entries, template_dir)

def main():
    """Main function."""
    print_colored("Nobl9 Error Budget Adjustment Script", Colors.CYAN)
    print_colored("=" * 40, Colors.CYAN)
    
    # Check dependencies
    check_dependencies()
    
    # Setup directories
    eba_files_dir, template_dir = setup_directories()
    
    # Get context
    context = get_available_contexts()
    
    # Fetch SLO data
    slos_data = fetch_slo_data()
    
    # Main menu loop
    while True:
        print_colored("\nMain Menu:", Colors.CYAN)
        print_colored("You can choose to deploy this adjustment to all SLOs in a Project or in a Service", Colors.YELLOW)
        print("  [1] List projects")
        print("  [2] List services")
        print("  [x] Exit")
        
        try:
            choice = input("Select an option: ").strip().lower()
            
            if choice == "1":
                list_projects(slos_data, template_dir)
            elif choice == "2":
                list_services(slos_data, template_dir)
            elif choice == "x":
                print_colored("Goodbye!", Colors.CYAN)
                sys.exit(0)
            # Invalid choice - just continue to reprompt
        except KeyboardInterrupt:
            print_colored("\nScript interrupted. Exiting.", Colors.RED)
            sys.exit(1)

if __name__ == "__main__":
    main() 