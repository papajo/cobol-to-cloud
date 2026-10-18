SHELL := /bin/bash
REF := $(shell cat legacy/CARDDEMO_REF)
IMG := c2c-legacy
JOB ?=
# Rootless Docker: container root == host user, so no -u (else -u maps to an unwritable subuid)
ROOTLESS := $(shell docker info --format '{{.SecurityOptions}}' 2>/dev/null | grep -q rootless && echo 1)
DUSER := $(if $(ROOTLESS),,-u $(shell id -u):$(shell id -g))
# Host mvn if present, else Maven 3.9 + JDK 21 in Docker (cache in .cache/m2)
MVN ?= $(if $(shell command -v mvn),mvn,docker run --rm $(DUSER) \
	-v $(CURDIR):/work -w /work -v $(CURDIR)/.cache/m2:/var/maven/.m2 -e MAVEN_CONFIG=/var/maven/.m2 \
	maven:3.9-eclipse-temurin-21 mvn -Duser.home=/var/maven)

.PHONY: fetch inventory seed-data legacy-build legacy-load legacy-unload legacy-run golden golden-all modern-test parity db-up db-reset

inventory:
	python3 mapper/inventory.py vendor/carddemo/app docs

# EBCDIC .PS → fixed ASCII records (ADR 0003). LRECLs from copybook headers.
SEED := ACCTDATA.PS:300:CVACT01Y CARDDATA.PS:150:CVACT02Y CARDXREF.PS:50:CVACT03Y CUSTDATA.PS:500:CVCUS01Y \
        DALYTRAN.PS:350:CVTRA06Y DALYTRAN.PS.INIT:350:CVTRA05Y DISCGRP.PS:50:CVTRA02Y TCATBALF.PS:50:CVTRA01Y TRANCATG.PS:60:CVTRA04Y TRANTYPE.PS:60:CVTRA03Y USRSEC.PS:80:CSUSR01Y
seed-data:
	@for s in $(SEED); do IFS=: read ds lrecl cpy <<< "$$s"; \
	  python3 migration/ebcdic2ascii.py vendor/carddemo/app/data/EBCDIC/AWS.M2.CARDDEMO.$$ds $$lrecl \
	    out/seed/AWS.M2.CARDDEMO.$$ds --copybook vendor/carddemo/app/cpy/$$cpy.cpy || exit 1; done

fetch:
	@test -d vendor/carddemo || git clone https://github.com/aws-samples/aws-mainframe-modernization-carddemo vendor/carddemo
	cd vendor/carddemo && git fetch --all -q && git checkout -q $(REF)

legacy-build:
	docker build -t $(IMG) legacy
	docker run --rm -v $(CURDIR):/work $(IMG) /work/legacy/build.sh

# IDCAMS DEFINE+REPRO equivalent: (re)create every KSDS from out/seed (baseline state)
legacy-load:
	docker run --rm -v $(CURDIR):/work $(IMG) python3 /work/legacy/vsam/load.py /work

# IDCAMS REPRO-out equivalent: KSDS → key-ordered flat files in out/legacy/unload (hashable)
legacy-unload:
	docker run --rm -v $(CURDIR):/work $(IMG) python3 /work/legacy/vsam/unload.py /work

legacy-run:
	@test -n "$(JOB)" || (echo "JOB=<member> required" && exit 1)
	@mkdir -p out/legacy && touch out/legacy/.runstart && sleep 1
	docker run --rm -e CD_BUSINESS_DATE=2022-07-18 -v $(CURDIR):/work $(IMG) \
		python3 /work/legacy/jcl-runner/jclrun.py /work/vendor/carddemo/app/jcl/$(JOB).jcl

# Baseline load → prerequisites (after=) → JOB → unload → capture; per-job MAXCC (see golden/jobs.txt)
golden:
	@test -n "$(JOB)" || (echo "JOB=<member> required" && exit 1)
	IMG=$(IMG) harness/golden.sh $(JOB)

golden-all:
	grep -v '^#' golden/jobs.txt | while read j rest; do [ -n "$$j" ] && { IMG=$(IMG) harness/golden.sh $$j || exit 1; }; done

modern-test:
	@mkdir -p .cache/m2
	$(MVN) -q -f modern/pom.xml verify

parity:
	@test -n "$(JOB)" || (echo "JOB=<member> required" && exit 1)
	python3 harness/compare.py golden/$(JOB) out/modern/$(JOB)

db-up:
	docker compose up -d db

db-reset:
	docker compose exec -T db psql -U carddemo -d carddemo -f /snapshots/baseline.sql
