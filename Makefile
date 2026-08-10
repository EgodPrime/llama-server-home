.PHONY: env serve clean

# Create Python environment
env:
	@if [ ! -d ".venv" ]; then uv venv .venv; fi
	uv pip install -e .

# Start service
serve:
	uv run llama-server-home

# Clean
clean:
	rm -rf .venv
