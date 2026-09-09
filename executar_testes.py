"""Executa a matriz minima de experimentos da Atividade 1 e grava um CSV."""

import argparse
import csv
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = WORKSPACE_DIR / "ollama-local-rag"
SOURCE_DATA_ROOT = WORKSPACE_DIR / "testes_rag"
ACTIVE_DOCS_PATH = PROJECT_DIR / "dados" / "documentos_ativos"
OUTPUT_DEFAULT = WORKSPACE_DIR / "resultados" / "resultados_atividade_1.csv"
QUERIES = {
    "curta": "Qual e o prazo para trocar as senhas corporativas?",
    "longa": (
        "Explique detalhadamente a politica de trabalho remoto, incluindo elegibilidade, "
        "requisitos tecnicos, equipamentos permitidos, horario de disponibilidade, "
        "seguranca, reembolso e acompanhamento semanal."
    ),
}
CONFIGURATIONS = {
    "padrao": {"dataset": "documentos_pequeno", "concurrency": 1, "k": 4, "description": "Base pequena, execucao sequencial com k=4"},
    "concorrencia": {"dataset": "documentos_grande", "concurrency": 2, "k": 4, "description": "Base grande, duas requisicoes simultaneas com k=4"},
    "ajuste_contexto": {"dataset": "documentos_grande", "concurrency": 1, "k": 2, "description": "Base grande, execucao sequencial com contexto reduzido, k=2"},
}


def environment_snapshot():
    """Collect lightweight Linux metrics without adding a runtime dependency."""
    try:
        processes = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,stat=,pcpu=,pmem=,nlwp=,comm="],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        processes = []

    relevant = []
    for line in processes:
        fields = line.split()
        if len(fields) >= 7 and fields[-1] in {"ollama", "python", "python3"}:
            relevant.append(fields)
    return {
        "processes": len(relevant),
        "threads": sum(int(item[5]) for item in relevant),
        "cpu_percent": round(sum(float(item[3]) for item in relevant), 2),
        "ram_percent": round(sum(float(item[4]) for item in relevant), 2),
    }


def disk_usage():
    total = 0
    for folder in (ACTIVE_DOCS_PATH, PROJECT_DIR / "faiss"):
        if folder.exists():
            total += sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())
    return total


def ollama_version():
    try:
        return subprocess.run(["ollama", "--version"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def command_output(command):
    try:
        return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def find_strace():
    candidates = [
        os.environ.get("STRACE_PATH", ""),
        shutil.which("strace") or "",
        "/tmp/strace-local/extracted/usr/bin/strace",
    ]
    return next((candidate for candidate in candidates if candidate and Path(candidate).is_file()), None)


def prepare_dataset(dataset_name):
    source = SOURCE_DATA_ROOT / dataset_name
    if not source.is_dir():
        raise FileNotFoundError(f"Conjunto de documentos nao encontrado: {source}")
    if ACTIVE_DOCS_PATH.exists():
        shutil.rmtree(ACTIVE_DOCS_PATH)
    shutil.copytree(source, ACTIVE_DOCS_PATH)
    return len([path for path in ACTIVE_DOCS_PATH.iterdir() if path.is_file()])


def runtime_environment():
    environment = os.environ.copy()
    environment["RAG_DATA_PATH"] = str(ACTIVE_DOCS_PATH)
    environment["RAG_FAISS_PATH"] = str(PROJECT_DIR / "faiss")
    return environment


def rebuild_index():
    subprocess.run(
        [sys.executable, "create_database.py"],
        cwd=PROJECT_DIR,
        env=runtime_environment(),
        check=True,
    )


def write_environment_csv(path):
    model_directories = [Path.home() / ".ollama" / "models", Path("/usr/share/ollama/.ollama/models")]
    model_directory = next((directory for directory in model_directories if directory.exists()), None)
    metrics = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "distribution": command_output(["sh", "-c", "cat /etc/os-release"]),
        "os_kernel": command_output(["uname", "-a"]),
        "cpu_details": command_output(["lscpu"]),
        "cpu_threads": command_output(["nproc"]),
        "memory": command_output(["free", "-h"]),
        "storage_available": command_output(["df", "-h", str(PROJECT_DIR)]),
        "block_devices": command_output(["lsblk"]),
        "gpu": command_output(["sh", "-c", "nvidia-smi 2>/dev/null || echo no NVIDIA GPU detected"]),
        "runtime": "Ollama",
        "runtime_version": ollama_version(),
        "models": command_output(["ollama", "list"]),
        "python_version": platform.python_version(),
        "strace_available": str(find_strace() is not None),
        "documents_and_index_bytes": str(disk_usage()),
        "model_storage": command_output(["du", "-sh", str(model_directory)]) if model_directory else "unavailable",
        "execution_environment": "WSL2/Linux (detected from uname)",
    }
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["metric", "value"])
        writer.writerows(metrics.items())


def write_strace_note(path):
    strace_path = find_strace()
    if strace_path:
        content = f"strace disponivel em {strace_path}; execute a captura com: {strace_path} -f -c -o resultados/strace-resumo.txt python query_data.py 'pergunta'\n"
    else:
        content = (
            "strace nao esta instalado neste ambiente WSL.\n"
            "Nenhuma chamada de sistema foi coletada automaticamente.\n"
            "Para executar a etapa solicitada pelo PDF, instale com: sudo apt-get install strace\n"
            "Depois execute: strace -f -c -o strace-resumo.txt python query_data.py 'pergunta'\n"
        )
    path.write_text(content, encoding="utf-8")


def write_summary_csv(rows, path):
    groups = {}
    for row in rows:
        key = (row["configuration"], row["input_size"])
        groups.setdefault(key, []).append(row)
    fields = [
        "configuration", "input_size", "executions", "successful_executions",
        "success_rate", "average_total_time_s", "minimum_total_time_s",
        "maximum_total_time_s", "average_cpu_percent", "average_ram_percent",
        "average_threads", "storage_docs_faiss_bytes",
    ]
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields)
        writer.writeheader()
        for (configuration, input_size), grouped_rows in groups.items():
            times = [float(row["total_time_s"]) for row in grouped_rows]
            successful = [row for row in grouped_rows if row["status"] == "ok"]
            writer.writerow({
                "configuration": configuration,
                "input_size": input_size,
                "executions": len(grouped_rows),
                "successful_executions": len(successful),
                "success_rate": round(len(successful) / len(grouped_rows), 3),
                "average_total_time_s": round(statistics.mean(times), 4),
                "minimum_total_time_s": round(min(times), 4),
                "maximum_total_time_s": round(max(times), 4),
                "average_cpu_percent": round(statistics.mean(float(row["cpu_percent_ollama_python"]) for row in grouped_rows), 2),
                "average_ram_percent": round(statistics.mean(float(row["ram_percent_ollama_python"]) for row in grouped_rows), 2),
                "average_threads": round(statistics.mean(float(row["threads_ollama_python"]) for row in grouped_rows), 2),
                "storage_docs_faiss_bytes": grouped_rows[0]["storage_docs_faiss_bytes"],
            })


def write_process_snapshot(path):
    output = command_output(["ps", "-eo", "pid=,ppid=,stat=,pcpu=,pmem=,nlwp=,comm=,args="])
    with path.open("w", encoding="utf-8") as output_file:
        output_file.write("pid,ppid,state,cpu_percent,ram_percent,threads,command,args\n")
        for line in output.splitlines():
            fields = line.split(None, 7)
            if len(fields) == 8 and fields[6] in {"ollama", "llama-server", "python", "python3"}:
                output_file.write(",".join(fields[:7]) + "," + fields[7].replace(",", " ") + "\n")


def write_latency_chart(rows, path):
    groups = {}
    for row in rows:
        key = f"{row['configuration']} / {row['input_size']}"
        groups.setdefault(key, []).append(float(row["total_time_s"]))
    averages = [(key, statistics.mean(values)) for key, values in groups.items()]
    maximum = max(value for _, value in averages) or 1
    width, height = 900, 430
    chart_left, chart_top, chart_width, chart_height = 220, 45, 620, 320
    bars = []
    for index, (label, value) in enumerate(averages):
        y = chart_top + index * (chart_height / len(averages))
        bar_width = value / maximum * chart_width
        bars.append(
            f'<text x="{chart_left - 10}" y="{y + 19:.1f}" text-anchor="end" font-size="14">{label}</text>'
            f'<rect x="{chart_left}" y="{y:.1f}" width="{bar_width:.1f}" height="24" fill="#2563eb"/>'
            f'<text x="{chart_left + bar_width + 8:.1f}" y="{y + 19:.1f}" font-size="14">{value:.2f}s</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="white"/>'
        '<text x="450" y="25" text-anchor="middle" font-size="18" font-weight="bold">Latencia media por cenario</text>'
        f'<line x1="{chart_left}" y1="{chart_top - 5}" x2="{chart_left}" y2="{chart_top + chart_height}" stroke="#374151"/>'
        f'<line x1="{chart_left}" y1="{chart_top + chart_height}" x2="{chart_left + chart_width}" y2="{chart_top + chart_height}" stroke="#374151"/>'
        + "".join(bars)
        + '<text x="530" y="420" text-anchor="middle" font-size="14">tempo total medio (segundos)</text></svg>'
    )
    path.write_text(svg, encoding="utf-8")


def run_one(configuration, input_size, repetition, document_count):
    query = QUERIES[input_size]
    command = [sys.executable, "query_data.py", query, "--k", str(configuration["k"])]
    before = environment_snapshot()
    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=600,
            env=runtime_environment(),
        )
        error = "" if completed.returncode == 0 else (completed.stderr.strip() or "processo retornou erro")
        status = "ok" if completed.returncode == 0 else "erro"
        answer_chars = len(completed.stdout.strip())
    except subprocess.TimeoutExpired as exception:
        error = f"timeout apos {exception.timeout}s"
        status = "timeout"
        answer_chars = 0
    except Exception as exception:
        error = f"{type(exception).__name__}: {exception}"
        status = "erro"
        answer_chars = 0

    elapsed = time.perf_counter() - started_at
    after = environment_snapshot()
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": configuration["name"],
        "configuration_description": configuration["description"],
        "dataset": configuration["dataset"],
        "document_count": document_count,
        "input_size": input_size,
        "input_chars": len(query),
        "repetition": repetition,
        "concurrency": configuration["concurrency"],
        "retrieved_chunks_k": configuration["k"],
        "status": status,
        "startup_time_s": "service_already_running",
        "total_time_s": round(elapsed, 4),
        "ttft_s": "unavailable_cli_only",
        "tokens_per_second": "unavailable_cli_only",
        "answer_chars": answer_chars,
        "response_valid": status == "ok" and answer_chars > 0,
        "evaluation_criterion": "resposta nao vazia e sem erro de execucao",
        "cpu_percent_ollama_python": max(before["cpu_percent"], after["cpu_percent"]),
        "ram_percent_ollama_python": max(before["ram_percent"], after["ram_percent"]),
        "processes_ollama_python": max(before["processes"], after["processes"]),
        "threads_ollama_python": max(before["threads"], after["threads"]),
        "storage_docs_faiss_bytes": disk_usage(),
        "model": "granite4.1:3b",
        "embedding_model": "nomic-embed-text",
        "runtime": "Ollama",
        "runtime_version": ollama_version(),
        "python_version": platform.python_version(),
        "error": error,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--rebuild-index", action="store_true", help="Recria o indice antes dos testes.")
    args = parser.parse_args()

    if args.repetitions < 2:
        parser.error("A atividade exige pelo menos duas repeticoes por cenario.")
    rows = []
    for configuration_name, values in CONFIGURATIONS.items():
        configuration = {"name": configuration_name, **values}
        document_count = prepare_dataset(configuration["dataset"])
        rebuild_index()
        for input_size in QUERIES:
            for repetition in range(1, args.repetitions + 1):
                if configuration["concurrency"] == 1:
                    rows.append(run_one(configuration, input_size, repetition, document_count))
                else:
                    with ThreadPoolExecutor(max_workers=configuration["concurrency"]) as executor:
                        futures = [executor.submit(run_one, configuration, input_size, repetition, document_count) for _ in range(configuration["concurrency"])]
                        rows.extend(future.result() for future in futures)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    write_environment_csv(args.output.with_name("ambiente_atividade_1.csv"))
    write_summary_csv(rows, args.output.with_name("resumo_atividade_1.csv"))
    write_process_snapshot(args.output.with_name("processos_atividade_1.csv"))
    write_latency_chart(rows, args.output.with_name("grafico_atividade_1.svg"))
    write_strace_note(args.output.with_name("strace-disponibilidade.txt"))
    print(f"Resultados gravados em {args.output} ({len(rows)} execucoes mensuraveis).")


if __name__ == "__main__":
    main()