run:
	@ mkdir -p dataset
	@ curl -s https://www.ine.es/jaxiT3/files/t/csv_bdsc/50904.csv -o "dataset/ipc.csv"

publish:
	@ uv run --with "huggingface_hub[cli]" huggingface-cli \
		upload --repo-type dataset datania/ipc dataset \
		--token $(HUGGINGFACE_TOKEN)
