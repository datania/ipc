.PHONY: run publish publish-check test-publish

run:
	@ mkdir -p dataset
	@ curl -s https://www.ine.es/jaxiT3/files/t/csv_bdsc/50904.csv -o "dataset/ipc.csv"

publish-check:
	@ uv run --locked --group publish hf upload --help > /dev/null

test-publish:
	@ uv run --locked --group publish python -m unittest discover -s tests -v

publish:
	@ test -n "$${HUGGINGFACE_TOKEN}" || { echo "HUGGINGFACE_TOKEN is required to publish" >&2; exit 1; }
	@ HF_TOKEN="$${HUGGINGFACE_TOKEN}" uv run --locked --group publish hf upload \
		--repo-type dataset datania/ipc dataset .
