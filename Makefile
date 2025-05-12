.PHONY: clean clean-build clean-pyc compile activate help 

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "compile - compile the project to an executable"
	@echo "compile-onefile - compile to a single executable file"
	@echo "install - install the package to the active Python's site-packages"
	@echo "test - run tests quickly with pytest"
	@echo "lint - check style with flake8"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr .eggs/

clean-pyc:
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*~' -delete
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '*.so' -delete
	find . -name '.coverage*' -delete
	find . -name 'htmlcov' -exec rm -fr {} +
	find . -name '.pytest_cache' -exec rm -fr {} +
	find . -name '.tox' -exec rm -fr {} +
	find . -name '*.spec' -delete

install:
	pip install -e .

compile: install
	pyinstaller src/core/services/web_crawler/crawler.py --name webcrawler --hidden-import=crawl4ai --hidden-import=chromadb --add-data="src/core/services/web_crawler/proxies.csv:src/core/services/web_crawler"

compile-onefile: install
	pyinstaller src/core/services/web_crawler/crawler.py --name webcrawler --onefile --hidden-import=crawl4ai --hidden-import=chromadb --add-data="src/core/services/web_crawler/proxies.csv:src/core/services/web_crawler"

app-compile: install
	pyinstaller src/core/services/web_crawler/app.py --name webcrawler-app --hidden-import=crawl4ai --hidden-import=chromadb --add-data="src/core/services/web_crawler/proxies.csv:src/core/services/web_crawler" --add-data="tasks.json:."

app-compile-onefile: install
	pyinstaller src/core/services/web_crawler/app.py --name webcrawler-app --onefile --hidden-import=crawl4ai --hidden-import=chromadb --add-data="src/core/services/web_crawler/proxies.csv:src/core/services/web_crawler" --add-data="tasks.json:."

activate:
	source .venv/bin/activate

run: install
	python src/core/services/web_crawler/app.py

run-with-tasks: install
	python src/core/services/web_crawler/app.py --tasks $(TASKS_FILE)

test: install
	pytest

lint:
	flake8 src tests
