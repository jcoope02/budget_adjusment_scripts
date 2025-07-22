#!/usr/bin/env python3
"""Error Budget Adjustment (EBA) Script - Interactive EBA YAML file creation."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("colorama is not installed. Please run: pip install colorama")
    sys.exit(1)


class Colors:
    """Color constants using colorama."""
    RED, GREEN, YELLOW, CYAN, WHITE = Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.CYAN, Fore.WHITE
    RESET = Style.RESET_ALL


def check_dependencies() -> None:
    """Check if required dependencies are installed."""
    for cmd, install_cmd, version_flag in [("jq", "brew install jq", "--version"), ("sloctl", "brew install nobl9/tap/sloctl", "version")]:
        try:
            subprocess.run([cmd, version_flag], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"{Colors.RED}{cmd} is not installed. Please run: {install_cmd}{Colors.RESET}")
            sys.exit(1)


def ensure_directories() -> Path:
    """Ensure required directories exist."""
    eba_files_dir = Path("./ebafiles")
    if not eba_files_dir.exists():
        eba_files_dir.mkdir(parents=True, exist_ok=True)
        print(f"{Colors.YELLOW}The directory {eba_files_dir} has been created.{Colors.RESET}")
    return eba_files_dir


def get_available_contexts() -> List[str]:
    """Fetch available sloctl contexts."""
    print(f"{Colors.CYAN}Fetching available contexts...{Colors.RESET}")
    try:
        result = subprocess.run(["sloctl", "config", "get-contexts"], capture_output=True, text=True, check=True)
        contexts = [ctx.strip() for ctx in result.stdout.strip().strip('[]').split(',') if ctx.strip()]
        if not contexts:
            print(f"{Colors.RED}No contexts available. Please configure Nobl9 contexts.{Colors.RESET}")
            sys.exit(1)
        return contexts
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}Failed to fetch contexts. Please check your Nobl9 configuration.{Colors.RESET}")
        sys.exit(1)


def select_from_list(items: List[str], prompt: str, item_type: str = "item") -> str:
    """Generic function to select from a list of items."""
    print(f"{Colors.CYAN}{item_type.title()}s:{Colors.RESET}")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")
    
    while True:
        try:
            selected_index = int(input(prompt)) - 1
            if 0 <= selected_index < len(items):
                selected_item = items[selected_index]
                print(f"{Colors.GREEN}Selected {item_type}: {selected_item}{Colors.RESET}")
                return selected_item
            print(f"{Colors.RED}Invalid selection.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")


def fetch_slo_data() -> List[Dict[str, Any]]:
    """Fetch SLO data from Nobl9."""
    print(f"{Colors.CYAN}Fetching SLO data from Nobl9...{Colors.RESET}")
    try:
        result = subprocess.run(["sloctl", "get", "slos", "-A", "-o", "json"], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print(f"{Colors.RED}Failed to fetch valid SLO data. Please check your Nobl9 configuration.{Colors.RESET}")
        sys.exit(1)


def get_user_input(field_name: str) -> str:
    """Get user input with validation for '#' character."""
    while True:
        user_input = input(f"Enter the {Colors.YELLOW}{field_name}{Colors.RESET} for the Budget Adjustment (no '#' allowed): ")
        if '#' not in user_input:
            return user_input
        print(f"{Colors.RED}The {field_name} cannot contain '#'. Please try again.{Colors.RESET}")


def validate_markdown_syntax(text: str) -> List[str]:
    """Validate markdown syntax and return list of issues."""
    issues = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines, 1):
        if line.count('**') % 2 != 0:
            issues.append(f"Line {i}: Unclosed bold markers (**)")
        if line.count('*') % 2 != 0 and '**' not in line:
            issues.append(f"Line {i}: Unclosed italic markers (*)")
        
        if '[' in line and '](' in line:
            if line.count('[') != line.count(']') or line.count('(') != line.count(')'):
                issues.append(f"Line {i}: Malformed link syntax")
            else:
                link_patterns = line.split('](')
                for pattern in link_patterns:
                    if pattern.startswith('[') and not pattern[1:].strip():
                        issues.append(f"Line {i}: Empty link text")
                    if pattern.endswith(')') and not pattern[:-1].strip():
                        issues.append(f"Line {i}: Empty link URL")
        
        if line.count('`') % 2 != 0:
            issues.append(f"Line {i}: Unclosed code markers (`)")
    
    return issues


def get_description() -> str:
    """Get description with markdown support and multi-line input."""
    print(f"\n{Colors.CYAN}Description (Markdown Supported){Colors.RESET}")
    print(f"{Colors.YELLOW}Examples: **bold**, *italic*, `code`, [text](url) for links{Colors.RESET}")
    print(f"{Colors.YELLOW}Press Enter twice to finish input.{Colors.RESET}")
    
    while True:
        lines = []
        while True:
            line = input().strip()
            if line == "" and lines:
                break
            if line == "" and not lines:
                continue
            lines.append(line)
        
        description = '\n'.join(lines).replace('\\n', '\n')
        issues = validate_markdown_syntax(description)
        
        if issues:
            print(f"\n{Colors.YELLOW}Markdown syntax issues found:{Colors.RESET}")
            for issue in issues:
                print(f"  {Colors.RED}• {issue}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}Do you want to fix these issues? (y/n): {Colors.RESET}").lower().strip()
            if choice == 'y':
                print(f"{Colors.CYAN}Please re-enter the description:{Colors.RESET}")
                continue
            else:
                print(f"{Colors.YELLOW}Proceeding with current description...{Colors.RESET}")
        
        return description


def get_event_duration() -> str:
    """Get event duration from user."""
    print(f"\n{Colors.CYAN}Event Duration{Colors.RESET}")
    print(f"{Colors.YELLOW}Format: Go-style duration (e.g., 1h30m for 1 hour 30 minutes){Colors.RESET}")
    
    while True:
        duration = input(f"Enter the {Colors.YELLOW}duration{Colors.RESET}: ").strip()
        if duration and all(c in '0123456789hms' for c in duration):
            if any(unit in duration for unit in ['h', 'm', 's']) and duration[0].isdigit():
                return duration
            else:
                print(f"{Colors.RED}Duration must include at least one time unit (h, m, or s) and start with a number.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Invalid format. Please use Go-style duration format (e.g., 1h30m).{Colors.RESET}")


def get_event_type() -> str:
    """Get event type (one-time vs recurring)."""
    print(f"\n{Colors.CYAN}Error Budget Adjustment Type{Colors.RESET}")
    print(f"  [1] One-time event (single occurrence)")
    print(f"  [2] Recurring event (repeats on schedule)")
    
    while True:
        try:
            choice = int(input("Select event type: "))
            if choice == 1:
                return "one-time"
            elif choice == 2:
                return "recurring"
            else:
                print(f"{Colors.RED}Invalid selection. Please choose 1 or 2.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")


def get_event_start(event_type: str) -> str:
    """Get event start date and time from user with validation based on type."""
    print(f"\n{Colors.CYAN}Event Start Date and Time{Colors.RESET}")
    print(f"{Colors.YELLOW}Format: YYYY-MM-DDThh:mm:ssZ (e.g., 2024-01-15T09:00:00Z){Colors.RESET}")
    
    if event_type == "recurring":
        print(f"{Colors.RED}Note: Recurring events must start in the future.{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}Note: One-time events can be in the past for historical adjustments.{Colors.RESET}")
    
    while True:
        event_start = input(f"Enter the {Colors.YELLOW}firstEventStart{Colors.RESET}: ").strip()
        
        if len(event_start) >= 19 and event_start[4] == '-' and event_start[7] == '-' and event_start[10] == 'T':
            try:
                event_datetime = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                current_datetime = datetime.now().replace(tzinfo=event_datetime.tzinfo)
                
                if event_type == "recurring" and event_datetime <= current_datetime:
                    print(f"{Colors.RED}Recurring events must start in the future. Please choose a future date.{Colors.RESET}")
                    continue
                
                return event_start
            except ValueError:
                print(f"{Colors.RED}Invalid datetime format. Please use YYYY-MM-DDThh:mm:ssZ format.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Invalid format. Please use YYYY-MM-DDThh:mm:ssZ format.{Colors.RESET}")


def get_rrule(event_type: str) -> str:
    """Get recurrence rule from user (only for recurring events)."""
    if event_type != "recurring":
        return ""
    
    print(f"\n{Colors.CYAN}Recurrence Rule (RRULE){Colors.RESET}")
    print(f"{Colors.YELLOW}Format: iCal RRULE format{Colors.RESET}")
    print(f"{Colors.YELLOW}Examples:{Colors.RESET}")
    print(f"  • FREQ=DAILY;INTERVAL=1 (daily)")
    print(f"  • FREQ=WEEKLY;INTERVAL=1;BYDAY=MO (weekly on Mondays)")
    print(f"  • FREQ=MONTHLY;INTERVAL=1;BYDAY=1TU (monthly on first Tuesday)")
    print(f"  • FREQ=DAILY;INTERVAL=3;COUNT=10 (every 3 days for 10 occurrences)")
    print(f"  • FREQ=WEEKLY;INTERVAL=1;UNTIL=20241231T235959Z (weekly until Dec 31, 2024)")
    
    while True:
        rrule = input(f"Enter the {Colors.YELLOW}RRULE{Colors.RESET}: ").strip()
        
        if not rrule:
            print(f"{Colors.RED}RRULE is required for recurring events.{Colors.RESET}")
            continue
        
        if rrule.upper().startswith('FREQ='):
            valid_freqs = ['FREQ=DAILY', 'FREQ=WEEKLY', 'FREQ=MONTHLY', 'FREQ=YEARLY']
            if any(freq in rrule.upper() for freq in valid_freqs):
                return rrule
            else:
                print(f"{Colors.RED}Invalid FREQ value. Use DAILY, WEEKLY, MONTHLY, or YEARLY.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Invalid RRULE format. Must start with FREQ= and follow iCal format.{Colors.RESET}")


def create_yaml_content(entity_name: str, slo_names: List[str], event_data: Dict[str, str]) -> str:
    """Create YAML content with embedded template and replacements."""
    template = f"""# Project/Service: {entity_name}
## This was generate by the EBA script for creating BudgetAdjustment objects in Nobl9.
## https://docs.nobl9.com/yaml-guide/#budgetadjustment
## https://docs.nobl9.com/features/budget-adjustments/
## https://registry.terraform.io/providers/nobl9/nobl9/latest/docs/resources/budget_adjustment
## https://icalendar.org/rrule-tool.html

apiVersion: n9/v1alpha
kind: BudgetAdjustment
metadata:
  name: {event_data['name']} # Mandatory
  displayName: {event_data['display_name']} # Optional
spec:
  description: # Optional
{event_data['description']}
  firstEventStart: {event_data['event_start']} # Mandatory, defined start date-time point
  duration: {event_data['event_duration']} # The duration of the budget adjustment event. hh:mm:ss
  {event_data['rrule_line']} # Optional, The expected value is a string in the iCal RRULE format.
  filters: # List of SLOs to which the adjustment applies will be auto-generated by the script and appear below
    slos:
"""
    
    # Add SLOs
    for slo_name in slo_names:
        template += f"      - name: {slo_name}\n        project: {entity_name}\n"
    
    return template


def create_eba_files(entity_name: str, slo_names: List[str], output_dir: Path, event_type: str = "") -> None:
    """Create Error Budget Adjustment YAML files."""
    if not event_type:
        event_type = get_event_type()
    event_start = get_event_start(event_type)
    event_duration = get_event_duration()
    rrule = get_rrule(event_type)
    display_name = get_user_input("displayName")
    description = get_description()
    
    # Generate name from display_name
    name = '-'.join(filter(None, ''.join(c.lower() if c.isalnum() else '-' for c in display_name).split('-')))
    current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    print("Creating Error Budget Adjustment YAML files...")
    
    # Format description for YAML
    if '\n' in description or '*' in description or '`' in description:
        formatted_description = f"|\n    {description.replace(chr(10), chr(10) + '    ')}"
    else:
        formatted_description = description
    
    # Prepare RRULE line
    rrule_line = f"rrule: {rrule}" if rrule else "# rrule:"
    
    event_data = {
        'name': name,
        'display_name': display_name,
        'description': formatted_description,
        'event_start': event_start,
        'event_duration': event_duration,
        'rrule_line': rrule_line
    }
    
    # Split SLOs into chunks of 30 for file splitting
    slo_chunks = [slo_names[i:i+30] for i in range(0, len(slo_names), 30)]
    
    for chunk_index, slo_chunk in enumerate(slo_chunks):
        # Add file index to name if multiple files
        file_suffix = f"-{chunk_index + 1}" if len(slo_chunks) > 1 else ""
        file_name = f"{name}{file_suffix}-{current_datetime}.yml"
        
        yaml_content = create_yaml_content(entity_name, slo_chunk, event_data)
        file_path = output_dir / file_name
        file_path.write_text(yaml_content)
        
        print(f"{Colors.GREEN}Created: {file_name} ({len(slo_chunk)} SLOs){Colors.RESET}")
    
    print(f"{Colors.GREEN}YAML files created in {output_dir}.{Colors.RESET}")


def process_entities(slos_data: List[Dict[str, Any]], entity_type: str, output_dir: Path) -> None:
    """Process projects or services."""
    print()
    
    # Get unique entities and their counts
    if entity_type == "project":
        entities = sorted(set(slo['metadata']['project'] for slo in slos_data))
        entity_slos = {entity: [slo for slo in slos_data if slo['metadata']['project'] == entity] for entity in entities}
    else:  # service
        entities = sorted(set(slo['spec'].get('service', 'N/A') for slo in slos_data))
        entity_slos = {entity: [slo for slo in slos_data if slo['spec'].get('service') == entity] for entity in entities}
    
    # Display entities with counts
    for i, entity in enumerate(entities, 1):
        count = len(entity_slos[entity])
        print(f"  [{i}] {entity} ({Colors.GREEN}{count}{Colors.RESET} SLOs)")
    
    # Remove redundant second print of projects
    # selected_entity = select_from_list(entities, f"Select a {entity_type} by number: ", entity_type)
    print()  # Add a blank line for readability
    while True:
        try:
            selected_index = int(input(f"Select a {entity_type} by number: ")) - 1
            if 0 <= selected_index < len(entities):
                selected_entity = entities[selected_index]
                print(f"{Colors.GREEN}Selected {entity_type}: {selected_entity}{Colors.RESET}")
                break
            print(f"{Colors.RED}Invalid selection.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")
    selected_slos = entity_slos[selected_entity]
    print(f"{Colors.CYAN}Number of SLOs in {selected_entity}: {Colors.GREEN}{len(selected_slos)}{Colors.RESET}")
    print(f"{Colors.YELLOW}SLOs:{Colors.RESET}")
    for slo in selected_slos:
        if entity_type == "project":
            service = slo['spec'].get('service', 'N/A')
            print(f"  {slo['metadata']['name']} [Service: {Colors.YELLOW}{service}{Colors.RESET}]")
        else:
            print(f"  {slo['metadata']['name']}")
    while True:
        print(f"{Colors.CYAN}Create Error Budget Adjustment YAML files?{Colors.RESET}")
        print(f"  [1] Yes - One-time event")
        print(f"  [2] Yes - Recurring event")
        print(f"  [3] No")
        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                slo_names = [slo['metadata']['name'] for slo in selected_slos]
                create_eba_files(selected_entity, slo_names, output_dir, "one-time")
                break
            elif choice == 2:
                slo_names = [slo['metadata']['name'] for slo in selected_slos]
                create_eba_files(selected_entity, slo_names, output_dir, "recurring")
                break
            elif choice == 3:
                print(f"{Colors.CYAN}Skipping YAML file creation.{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid selection. Please choose 1, 2, or 3.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")


def process_individual_slos(slos_data: List[Dict[str, Any]], output_dir: Path) -> None:
    """Process individual SLOs with multiple selection support."""
    print()
    print(f"{Colors.YELLOW}Individual SLOs:{Colors.RESET}")
    
    # Display all SLOs with their project and service info
    for i, slo in enumerate(slos_data, 1):
        project = slo['metadata']['project']
        service = slo['spec'].get('service', 'N/A')
        slo_name = slo['metadata']['name']
        print(f"  [{i}] {slo_name} [Project: {Colors.CYAN}{project}{Colors.RESET}, Service: {Colors.YELLOW}{service}{Colors.RESET}]")
    
    print(f"\n{Colors.CYAN}Enter SLO numbers separated by commas (e.g., 1,3,5) or 'all' for all SLOs:{Colors.RESET}")
    
    while True:
        try:
            selection = input("Selection: ").strip().lower()
            
            if selection == 'all':
                selected_indices = list(range(1, len(slos_data) + 1))
                break
            else:
                selected_indices = [int(idx.strip()) for idx in selection.split(',') if idx.strip()]
                
                if all(1 <= idx <= len(slos_data) for idx in selected_indices):
                    break
                else:
                    print(f"{Colors.RED}Invalid selection. Please enter valid numbers between 1 and {len(slos_data)}.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter numbers separated by commas.{Colors.RESET}")
    
    # Get selected SLOs
    selected_slos = [slos_data[idx - 1] for idx in selected_indices]
    selected_names = [slo['metadata']['name'] for slo in selected_slos]
    
    print(f"\n{Colors.GREEN}Selected {len(selected_slos)} SLO(s):{Colors.RESET}")
    for slo in selected_slos:
        project = slo['metadata']['project']
        service = slo['spec'].get('service', 'N/A')
        print(f"  {slo['metadata']['name']} [Project: {Colors.CYAN}{project}{Colors.RESET}, Service: {Colors.YELLOW}{service}{Colors.RESET}]")
    
    while True:
        print(f"\n{Colors.CYAN}Create Error Budget Adjustment YAML files?{Colors.RESET}")
        print(f"  [1] Yes - One-time event")
        print(f"  [2] Yes - Recurring event")
        print(f"  [3] No")
        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                project_name = selected_slos[0]['metadata']['project'] if selected_slos else "default"
                create_eba_files(project_name, selected_names, output_dir, "one-time")
                break
            elif choice == 2:
                project_name = selected_slos[0]['metadata']['project'] if selected_slos else "default"
                create_eba_files(project_name, selected_names, output_dir, "recurring")
                break
            elif choice == 3:
                print(f"{Colors.CYAN}Skipping YAML file creation.{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid selection. Please choose 1, 2, or 3.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")


def main() -> None:
    """Main function."""
    check_dependencies()
    output_dir = ensure_directories()
    
    contexts = get_available_contexts()
    selected_context = select_from_list(contexts, "Welcome to the Error Budget Adjustment script - please select a sloctl context to use by number: ", "context")
    subprocess.run(["sloctl", "config", "use-context", selected_context], check=True, capture_output=True)
    
    slos_data = fetch_slo_data()
    
    while True:
        print(f"\n{Colors.CYAN}Please choose how you would like to sort the SLOs?{Colors.RESET}")
        print("  [1] List projects\n  [2] List services\n  [3] List individual SLOs\n  [0] Exit")
        
        try:
            choice = int(input("Select an option: "))
            if choice == 0:
                print(f"{Colors.CYAN}Goodbye!{Colors.RESET}")
                break
            elif choice in [1, 2]:
                process_entities(slos_data, "project" if choice == 1 else "service", output_dir)
            elif choice == 3:
                process_individual_slos(slos_data, output_dir)
            else:
                print(f"{Colors.RED}Invalid selection. Please choose a valid option.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")


if __name__ == "__main__":
    main() 