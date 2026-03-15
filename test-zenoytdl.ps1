echo "============================================================"
echo "🔧 PREPARACIÓN DEL ENTORNO"
echo "============================================================"

git pull
python -m pip install -U pip
python -m pip install -e .[dev]
python -m ruff check src tests

echo ""
echo "============================================================"
echo "🧪 BATERÍA GENERAL DE TESTS"
echo "============================================================"

python -m pytest tests/unit
python -m pytest tests/integration
python -m pytest tests/e2e
python -m pytest tests/regression

echo ""
echo "============================================================"
echo "🏷️ TESTS POR MARCADORES"
echo "============================================================"

python -m pytest tests/unit -m unit
python -m pytest tests/integration -m integration
python -m pytest tests/e2e -m e2e
python -m pytest tests/regression -m regression

echo ""
echo "============================================================"
echo "📄 YAML CONTRACT"
echo "============================================================"

python -m pytest tests/unit/test_yaml_contract.py tests/integration/test_yaml_contract_consistency.py tests/e2e/test_yaml_contract_flow.py tests/regression/test_hito3_yaml_contract_regression.py

echo ""
echo "============================================================"
echo "⚙️ CONFIG LOADER"
echo "============================================================"

python -m pytest tests/unit/test_config_loader.py
python -m pytest tests/integration/test_config_loader_domain_integration.py
python -m pytest tests/e2e/test_config_loader_flow.py
python -m pytest tests/regression/test_hito4_config_loader_regression.py

echo ""
echo "============================================================"
echo "✅ CONFIG VALIDATION"
echo "============================================================"

python -m pytest tests/unit/test_config_validation.py tests/integration/test_config_validation_integration.py tests/e2e/test_config_validation_flow.py tests/regression/test_hito5_validation_regression.py

echo ""
echo "============================================================"
echo "🧩 EFFECTIVE RESOLUTION"
echo "============================================================"

python -m pytest tests/unit/test_effective_resolution.py
python -m pytest tests/integration/test_effective_resolution_integration.py
python -m pytest tests/e2e/test_effective_resolution_flow.py
python -m pytest tests/regression/test_hito6_effective_resolution_regression.py

echo ""
echo "============================================================"
echo "🛡️ OVERRIDE POLICIES"
echo "============================================================"

python -m pytest tests/unit/test_override_policies.py
python -m pytest tests/integration/test_override_policies_integration.py
python -m pytest tests/e2e/test_override_policies_flow.py
python -m pytest tests/regression/test_hito7_override_policies_regression.py

echo ""
echo "------------------------------------------------------------"
echo "🔁 OVERRIDE POLICIES · EJECUCIÓN AGRUPADA"
echo "------------------------------------------------------------"

python -m pytest tests/unit/test_override_policies.py tests/integration/test_override_policies_integration.py tests/e2e/test_override_policies_flow.py tests/regression/test_hito7_override_policies_regression.py

echo ""
echo "============================================================"
echo "🧱 POSTPROCESSING RESOLUTION"
echo "============================================================"

python -m pytest tests/unit/test_postprocessing_resolution.py tests/integration/test_postprocessing_integration.py tests/e2e/test_postprocessing_flow.py tests/regression/test_hito8_postprocessing_regression.py

echo ""
echo "============================================================"
echo "🎞️ YTDL SUB CONTRACT"
echo "============================================================"

python -m pytest tests/unit/test_ytdl_sub_contract.py
python -m pytest tests/integration/test_ytdl_sub_contract_integration.py
python -m pytest tests/e2e/test_ytdl_sub_contract_flow.py
python -m pytest tests/regression/test_hito9_ytdl_sub_contract_regression.py

echo ""
echo "============================================================"
echo "🌍 YTDL SUB TRANSLATION"
echo "============================================================"

python -m pytest tests/unit/test_ytdl_sub_translation.py
python -m pytest tests/integration/test_ytdl_sub_translation_integration.py
python -m pytest tests/e2e/test_ytdl_sub_translation_flow.py
python -m pytest tests/regression/test_hito10_ytdl_sub_translation_regression.py

echo ""
echo "============================================================"
echo "📦 ARTIFACT COMPILER"
echo "============================================================"

python -m pytest tests/unit/test_artifact_compiler.py
python -m pytest tests/integration/test_artifact_compiler_integration.py
python -m pytest tests/e2e/test_artifact_compiler_flow.py
python -m pytest tests/regression/test_hito11_artifact_compilation_regression.py

echo ""
echo "============================================================"
echo "🚀 YTDL SUB EXECUTOR"
echo "============================================================"

python -m pytest tests/unit/test_ytdl_sub_executor.py
python -m pytest tests/integration/test_ytdl_sub_executor_integration.py
python -m pytest tests/e2e/test_ytdl_sub_executor_flow.py
python -m pytest tests/regression/test_hito12_ytdl_sub_executor_regression.py

echo ""
echo "============================================================"
echo "💾 SQLITE OPERATIONAL STATE · HITO 13"
echo "============================================================"

python -m pytest tests/unit/test_sqlite_operational_state.py
python -m pytest tests/integration/test_hito13_persistence_integration.py
python -m pytest tests/e2e/test_hito13_persistence_flow.py
python -m pytest tests/regression/test_hito13_persistence_regression.py

echo ""
echo "============================================================"
echo "🚫 ANTI-REDOWNLOAD · HITO 14"
echo "============================================================"

python -m pytest tests/unit/test_sqlite_operational_state.py -k hito14
python -m pytest tests/integration/test_hito14_anti_redownload_integration.py
python -m pytest tests/e2e/test_hito14_anti_redownload_flow.py
python -m pytest tests/regression/test_hito14_anti_redownload_regression.py

echo ""
echo "============================================================"
echo "🗂️ RETENTION · HITO 15"
echo "============================================================"

python -m pytest tests/unit/test_sqlite_operational_state.py -k hito15
python -m pytest tests/integration/test_hito15_retention_integration.py
python -m pytest tests/e2e/test_hito15_retention_flow.py
python -m pytest tests/regression/test_hito15_retention_regression.py

echo ""
echo "============================================================"
echo "🧠 CACHE SYSTEM · HITO 16"
echo "============================================================"

python -m pytest tests/unit/test_hito16_cache_system.py
python -m pytest tests/integration/test_hito16_cache_integration.py
python -m pytest tests/e2e/test_hito16_cache_flow.py
python -m pytest tests/regression/test_hito16_cache_regression.py

echo ""
echo "============================================================"
echo "🧠 QUEUE SYSTEM · HITO 17"
echo "============================================================"
python -m pytest tests/unit/test_hito17_queue_models.py
python -m pytest tests/unit/test_sqlite_operational_state.py -k hito17
python -m pytest tests/integration/test_hito17_queue_integration.py
python -m pytest tests/e2e/test_hito17_queue_flow.py
python -m pytest tests/regression/test_hito17_queue_regression.py

echo ""
echo "============================================================"
echo "🛠️ UTILIDADES Y COMPROBACIONES FINALES"
echo "============================================================"

.\scripts\bootstrap-dev.ps1
python -m src.api.cli --config tests/fixtures/clean/minimal.yaml

ytdl-sub --version
ffmpeg -version
ffprobe -version

echo ""
echo "============================================================"
echo "✅ FIN DE LA EJECUCIÓN"
echo "============================================================"
