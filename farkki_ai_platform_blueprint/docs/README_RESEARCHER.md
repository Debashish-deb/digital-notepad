# Farkki-AI Clinical-Spatial Research Copilot: Researcher Guide

Welcome to the Farkki-AI Research Copilot! This platform assists laboratory researchers with multiplex image-processing pipelines (tCyCIF), high-performance computing (LUMI), environment checks, and script generation.

## 🚀 Key Interface Tabs

### 1. 💬 Chat Copilot
* Chat with a multi-agent backend assistant about documentation and codebase parameters.
* **Important**: Direct patient identifiers (SSNs, DOBs, MRNs) are audited and redacted by the privacy guardrails. De-identify your data prior to input.
* Review references by expanding the **References** section below any response.

### 2. 📊 Database Explorer
* Monitor cohorts and registry statistics.
* Slices metrics dynamically based on project scopes selected in the sidebar (e.g., `SPACE`, `EyeMT`, or `KRAS`).

### 3. 🛠️ Install Software
* Installs complex tools (e.g., Napari, Cylinter, StarDist) across different OS profiles (Windows, macOS, Linux).
* Returns exact commands, expected outputs, verification instructions, and recovery options.

### 4. 💻 Generate LUMI Job
* Inputs project parameters and compiles verified Slurm job submission scripts.
* Follows safety guardrails (writes files to scratch partitions, limits output logs, checks directories).

### 5. 🩺 Env Checker
* Verifies local system environment configurations (CUDA drivers, Python modules, folder paths) directly on the machine.
* Generates detailed diagnostics.

### 6. 🔍 Troubleshoot Error
* Paste tracebacks, package conflicts, or Slurm errors.
* Returns a diagnosis and fix instructions.
