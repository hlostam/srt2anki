.PHONY: default isvirtualenv

# Makefile variables
VENV_NAME:=venv
PYTHON=${VENV_NAME}/bin/python3

## Checks whether is a virtual environment set
isvirtualenv:
	@if [ -z "$(VIRTUAL_ENV)" ]; then echo "ERROR: Not in a virtualenv." 1>&2; exit 1; fi

## Delete all compiled Python files
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

## Lint using flake8
lint:
	flake8 src 

# lint: venv
# 	${PYTHON} -m pylint main.py

## Clean output of jupyter notebooks
clean_nb_%:
	jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace notebooks/$*.ipynb

## Clean output of all jupyter notebooks
cleanall_nb: $(patsubst notebooks/%.ipynb,clean_nb_%,$(wildcard notebooks/*.ipynb))

## Creates a virtual environment
venv:
	python3 -m venv $(VENV_NAME)

# venv2: $(VENV_NAME)/bin/activate
# $(VENV_NAME)/bin/activate: 
# 	test -d $(VENV_NAME) || python3 -m venv $(VENV_NAME)
# 	touch $(VENV_NAME)/bin/activate
# 	. ${VENV_NAME}/activate && exec bash

## Freezes the environment
pipfreeze: isvirtualenv
	pip3 freeze > requirements.txt

pipinstall: isvirtualenv
	pip3 install --upgrade pip
	pip3 install -r requirements.txt
	pip3 install --editable .

data/raw:
	@echo "Fetching raw data..."
	mkdir -p $@

run: venv pipinstall

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
