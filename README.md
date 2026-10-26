# Índice de Precios de Consumo 🛒

[![Run](https://github.com/datania/ipc/actions/workflows/run.yml/badge.svg)](https://github.com/datania/ipc/actions/workflows/run.yml)

Datos históricos del Índice de Precios de Consumo (IPC) de España, [accessibles en HuggingFace](https://huggingface.co/datasets/datania/ipc).

## Publicación

Con [uv](https://docs.astral.sh/uv/) instalado, `make publish-check` comprueba
que la CLI de publicación está disponible sin subir datos ni usar credenciales.
`make publish` sube el contenido de `dataset/` a la raíz de `datania/ipc`.
Requiere `HUGGINGFACE_TOKEN` en el entorno; GitHub Actions usa el secreto existente
con ese nombre. El token se transmite mediante `HF_TOKEN`, sin incluirlo en los
argumentos de la CLI.

La publicación usa [`hf upload`](https://huggingface.co/docs/huggingface_hub/guides/cli#hf-upload)
con las versiones de `pyproject.toml` y `uv.lock`. Para actualizar la CLI,
cambia su versión en el grupo `publish`, ejecuta `uv lock` y vuelve a comprobar
`make publish-check test-publish`.

`make test-publish` prueba el Makefile y la CLI real con un servidor HTTP local,
datos temporales y un token ficticio: comprueba el destino y contenido subido,
la propagación de errores y que el token no aparezca en la salida. No publica
datos en Hugging Face ni necesita credenciales reales.
