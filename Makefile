PYTHON ?= python3

.PHONY: test demo lint

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

demo:
	sh scripts/demo.sh

lint:
	$(PYTHON) scripts/check_style.py
