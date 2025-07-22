# Error Budget Adjustment Script

**eba.py** is an advanced, interactive command-line tool for creating Error Budget Adjustment (EBA) YAML files for Nobl9 SLOs. It fetches SLO data from Nobl9, allows you to select projects, services, or individual SLOs, and generates ready-to-use YAML files with rich user input and validation.

## What does it do?
- Connects to your Nobl9 environment using the `sloctl` CLI.
- Fetches all available SLOs and organizes them by project, service, or lets you select individual SLOs.
- Lets you interactively select a project, service, or multiple SLOs for which you want to create an error budget adjustment.
- Prompts you for display name, a multi-line markdown-formatted description (with syntax validation), event type (one-time or recurring), event start, duration, and RRULE (for recurring events).
- Generates YAML files with all required fields, using an embedded template (no external template files needed).
- Splits output into multiple files if there are more than 30 SLOs.
- Provides color-coded, user-friendly terminal output (cross-platform with colorama).

## Key Features
- Interactive terminal prompts for all required fields
- Multi-line, markdown-supported descriptions with syntax validation
- Choose event type (one-time or recurring) and specify RRULE for recurring events
- Select by project, service, or individual SLOs (multi-select)
- Embedded YAML template (no need for external template files)
- Color-coded output for clarity (works on Windows, macOS, Linux)
- Robust error handling and user guidance

## Typical Workflow
1. **Run the script:**
   ```sh
   python eba.py
   ```
2. **Select Nobl9 context:**
   - Choose from available `sloctl` contexts.
3. **Choose how to sort SLOs:**
   - By project, service, or individual SLOs.
4. **Select entities/SLOs:**
   - Pick a project, service, or multiple SLOs.
5. **Enter details:**
   - Display name, description (markdown supported), event type, start, duration, RRULE.
6. **YAML generation:**
   - The script generates one or more YAML files in the `ebafiles/` directory, batching SLOs as needed.
7. **Review and use:**
   - Review the generated YAMLs and use them with Nobl9 as needed.

## License
See [LICENSE](LICENSE) for details. 