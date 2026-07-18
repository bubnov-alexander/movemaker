#!/usr/bin/env bash
# Этот файл должен храниться с Unix-переносами строк (LF).
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "Не найдено виртуальное окружение .venv. Установите зависимости проекта." >&2
    exit 1
fi

if ! CUBLAS_DIR="$("$PYTHON" -c 'import inspect, os, nvidia.cublas.lib; print(os.path.dirname(inspect.getfile(nvidia.cublas.lib)))' 2>/dev/null)"; then
    echo "Не найдена CUDA-библиотека cuBLAS. Выполните: .venv/bin/pip install -U nvidia-cublas-cu12 nvidia-cudnn-cu12" >&2
    exit 1
fi

if ! CUDNN_DIR="$("$PYTHON" -c 'import inspect, os, nvidia.cudnn.lib; print(os.path.dirname(inspect.getfile(nvidia.cudnn.lib)))' 2>/dev/null)"; then
    echo "Не найдена CUDA-библиотека cuDNN. Выполните: .venv/bin/pip install -U nvidia-cublas-cu12 nvidia-cudnn-cu12" >&2
    exit 1
fi

if [[ ! -f "$CUBLAS_DIR/libcublas.so.12" || ! -f "$CUDNN_DIR/libcudnn.so.9" ]]; then
    echo "CUDA-библиотеки установлены не полностью. Выполните: .venv/bin/pip install -U nvidia-cublas-cu12 nvidia-cudnn-cu12" >&2
    exit 1
fi

export LD_LIBRARY_PATH="$CUBLAS_DIR:$CUDNN_DIR:${LD_LIBRARY_PATH:-}"
exec "$PROJECT_DIR/.venv/bin/movie-shorts" "$@"
