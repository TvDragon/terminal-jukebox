VIRTUAL_ENV = $(CURDIR)/env

ifeq ($(OS),Windows_NT)
	PYTHON = $(VIRTUAL_ENV)/Scripts/python.exe
	PIP = $(VIRTUAL_ENV)/Scripts/pip.exe
	DATA_SEP = ;
else
	PYTHON = $(VIRTUAL_ENV)/bin/python
	PIP = $(VIRTUAL_ENV)/bin/pip
	DATA_SEP = :
endif

.PHONY: install build clean test

$(VIRTUAL_ENV):
	python3 -m venv $(VIRTUAL_ENV)

install: $(VIRTUAL_ENV)
	$(PIP) install -r requirements.txt

build: $(VIRTUAL_ENV)
	$(PYTHON) -m PyInstaller --onefile \
		--name terminal-jukebox \
		src/main.py \
		--collect-submodules textual \
		--collect-submodules just_playback \
		--collect-all cffi \
		--add-data "src/terminal-jukebox.tcss$(DATA_SEP)."

clean:
	rm -rf build dist terminal-jukebox.spec
	rm -rf $(VIRTUAL_ENV)

test: $(VIRTUAL_ENV)
	PYTHONPATH=$(CURDIR)/src $(PYTHON) -m main