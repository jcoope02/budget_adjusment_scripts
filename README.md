# Error Budget Adjustment Script

**ebascript** is a command-line tool for automating the creation of Error Budget Adjustment (EBA) YAML files for Nobl9 SLOs. It interactively fetches SLO data from Nobl9, allows you to select projects or services, and generates ready-to-use YAML templates for error budget adjustments.

## What does it do?
- Connects to your Nobl9 environment using the `sloctl` CLI.
- Fetches all available SLOs and organizes them by project or service.
- Lets you interactively select a project or service for which you want to create an error budget adjustment.
- Prompts you for display name and description, and lets you choose a template.
- Automatically generates one or more YAML files, each containing up to 30 SLOs, ready for use with Nobl9.
- Ensures all required fields are filled and provides guidance for further manual edits (such as time and duration fields).

## Key Features
- Interactive terminal prompts for easy selection and input
- Automatic grouping and batching of SLOs
- Template-based YAML generation
- Color-coded output for clarity
- Handles missing dependencies and setup automatically

## Typical Use Case
You want to quickly generate error budget adjustment YAMLs for all SLOs in a specific project or service in your Nobl9 account, using a consistent template and with minimal manual editing.

## License
See [LICENSE](LICENSE) for details. 