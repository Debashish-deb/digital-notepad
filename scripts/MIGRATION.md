# Scripts path migration

Scripts were reorganized from a flat `scripts/` directory into category subfolders. **Backward-compat wrappers** at the old flat paths delegate to the new locations.

## Shell scripts

| Old path | New path |
|----------|----------|
| `scripts/start_backend.sh` | `scripts/dev/start_backend.sh` |
| `scripts/start_frontend.sh` | `scripts/dev/start_frontend.sh` |
| `scripts/start_portable.sh` | `scripts/dev/start_portable.sh` |
| `scripts/load_env.sh` | `scripts/dev/load_env.sh` |
| `scripts/docker_bootstrap.sh` | `scripts/dev/docker_bootstrap.sh` |
| `scripts/stop_local_docker.sh` | `scripts/dev/stop_local_docker.sh` |
| `scripts/00_bootstrap.sh` | `scripts/dev/00_bootstrap.sh` |
| `scripts/autonomous_processor.sh` | `scripts/ops/autonomous_processor.sh` |
| `scripts/setup_search_portable.sh` | `scripts/search/setup_search_portable.sh` |
| `scripts/setup_research_knowledge.sh` | `scripts/document-library/setup_research_knowledge.sh` |
| `scripts/build_imaging_worker.sh` | `scripts/docker/build_imaging_worker.sh` |
| `scripts/setup_biomodels_docker.sh` | `scripts/docker/setup_biomodels_docker.sh` |
| `scripts/start_linux_docker_stack.sh` | `scripts/docker/start_linux_docker_stack.sh` |
| `scripts/generate_ollama_token.sh` | `scripts/llm/generate_ollama_token.sh` |
| `scripts/setup_ollama_local_llm.sh` | `scripts/llm/setup_ollama_local_llm.sh` |
| `scripts/pull_ollama_research_models.sh` | `scripts/llm/pull_ollama_research_models.sh` |
| `scripts/ollama_ssh_tunnel.sh` | `scripts/llm/ollama_ssh_tunnel.sh` |
| `scripts/linux_fix_tailscale_inbound.sh` | `scripts/network/linux_fix_tailscale_inbound.sh` |
| `scripts/setup_mac_portable.sh` | `scripts/network/setup_mac_portable.sh` |
| `scripts/portable_apply_env.sh` | `scripts/network/portable_apply_env.sh` |
| `scripts/mac_test_tailscale_ollama.sh` | `scripts/network/mac_test_tailscale_ollama.sh` |
| `scripts/mac_connect_linux.sh` | `scripts/network/mac_connect_linux.sh` |
| `scripts/mac_test_linux.sh` | `scripts/network/mac_test_linux.sh` |
| `scripts/linux_tunnel_to_mac.sh` | `scripts/network/linux_tunnel_to_mac.sh` |
| `scripts/linux_enable_tailscale_ssh.sh` | `scripts/network/linux_enable_tailscale_ssh.sh` |
| `scripts/sync_mac_repo_to_usb.sh` | `scripts/network/sync_mac_repo_to_usb.sh` |
| `scripts/linux_paste_install_imaging_worker.sh` | `scripts/imaging/linux_paste_install_imaging_worker.sh` |
| `scripts/linux_minimal_imaging_capabilities.sh` | `scripts/imaging/linux_minimal_imaging_capabilities.sh` |
| `scripts/pack_imaging_worker_bundle.sh` | `scripts/imaging/pack_imaging_worker_bundle.sh` |
| `scripts/sync_imaging_worker_to_linux.sh` | `scripts/imaging/sync_imaging_worker_to_linux.sh` |
| `scripts/copy_imaging_bundle_to_linux.sh` | `scripts/imaging/copy_imaging_bundle_to_linux.sh` |
| `scripts/check_python_env.sh` | `scripts/check/check_python_env.sh` |
| `scripts/check_gpu.sh` | `scripts/check/check_gpu.sh` |
| `scripts/check_napari.sh` | `scripts/check/check_napari.sh` |
| `scripts/check_docker.sh` | `scripts/check/check_docker.sh` |
| `scripts/check_lumi_modules.sh` | `scripts/check/check_lumi_modules.sh` |

## Python scripts

| Old path | New path |
|----------|----------|
| `scripts/autonomous_processor.py` | `scripts/ops/autonomous_processor.py` |
| `scripts/scheduled_ingest.py` | `scripts/ops/scheduled_ingest.py` |
| `scripts/validate_manifests.py` | `scripts/ops/validate_manifests.py` |
| `scripts/validate_platform.py` | `scripts/ops/validate_platform.py` |
| `scripts/query_copilot_demo.py` | `scripts/ops/query_copilot_demo.py` |
| `scripts/create_qdrant_collections.py` | `scripts/ingest/create_qdrant_collections.py` |
| `scripts/ingest_documents_demo.py` | `scripts/ingest/ingest_documents_demo.py` |
| `scripts/apply_sql_migrations.py` | `scripts/database/apply_sql_migrations.py` |
| `scripts/ingest_database.py` | `scripts/database/ingest_database.py` |
| `scripts/synthetic_seed_data.py` | `scripts/database/synthetic_seed_data.py` |
| `scripts/sync_documents_to_supabase.py` | `scripts/sync/sync_documents_to_supabase.py` |
| `scripts/run_ai_lab_assistant_eval.py` | `scripts/search/run_ai_lab_assistant_eval.py` |
| `scripts/run_digitalization.py` | `scripts/digitalization/run_digitalization.py` |
| `scripts/build_raw_asset_inventory.py` | `scripts/digitalization/build_raw_asset_inventory.py` |
| `scripts/project_digitalize.py` | `scripts/digitalization/project_digitalize.py` |
| `scripts/check_cylinter_inputs.py` | `scripts/check/check_cylinter_inputs.py` |
| `scripts/check_tcycif_project_structure.py` | `scripts/check/check_tcycif_project_structure.py` |

## API checker paths

`app_skeleton/api/paths.py` `CHECKER_SCRIPTS` now uses `check/<script>` relative to `SCRIPTS_DIR`.

## Path resolution changes

- **Shell:** `ROOT` / `PROJECT_ROOT` / `REPO_ROOT` must use `../..` from category subdirs (or `scripts/lib/common.sh`).
- **Python:** `Path(__file__).resolve().parents[2]` for repo root (was `parents[1]` when scripts were flat).
