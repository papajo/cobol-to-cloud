SHELL := /bin/bash
REF := $(shell cat legacy/CARDDEMO_REF)
IMG := c2c-legacy
JOB ?=

.PHONY: fetch legacy-build legacy-run golden golden-all modern-test parity db-up db-reset

fetch:
	@test -d vendor/carddemo || git clone https://github.com/aws-samples/aws-mainframe-modernization-carddemo vendor/carddemo
	cd vendor/carddemo && git fetch --all -q && git checkout -q $(REF)

legacy-build:
	docker build -t $(IMG) legacy
	docker run --rm -v $(PWD):/work $(IMG) /work/legacy/build.sh

legacy-run:
	@test -n "$(JOB)" || (echo "JOB=<member> required" && exit 1)
	docker run --rm -e CD_BUSINESS_DATE=2022-07-18 -v $(PWD):/work $(IMG) \
		python3 /work/legacy/jcl-runner/jclrun.py /work/vendor/carddemo/app/jcl/$(JOB).jcl

golden: legacy-run
	python3 harness/capture.py $(JOB)

golden-all:
	while read j; do $(MAKE) golden JOB=$$j || exit 1; done < golden/jobs.txt

modern-test:
	mvn -q -f modern/pom.xml verify

parity:
	@test -n "$(JOB)" || (echo "JOB=<member> required" && exit 1)
	python3 harness/compare.py golden/$(JOB) out/modern/$(JOB)

db-up:
	docker compose up -d db

db-reset:
	docker compose exec -T db psql -U carddemo -d carddemo -f /snapshots/baseline.sql
