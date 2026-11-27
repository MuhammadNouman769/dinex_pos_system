.PHONY: help setup dev backend web demo test build clean
help:           ## list commands
	@grep -E '^[a-z]+:.*##' Makefile | sed 's/:.*##/\t/'
setup:          ## one-time: venv, packages, database, demo data, npm install
	./scripts/dev-setup.sh
dev:            ## run backend :8000 and web :3000 together
	./scripts/dev.sh
backend:        ## backend only
	cd dinex && . venv/bin/activate && python manage.py runserver 8000
web:            ## frontend only
	cd dinex-web && npm run dev
demo:           ## reset the database and reload demo data
	cd dinex && . venv/bin/activate && python manage.py seed_demo --reset
test:           ## backend tests + frontend type check
	./scripts/test.sh
build:          ## production build of the frontend
	cd dinex-web && npm run build
clean:          ## remove build output and caches
	rm -rf dinex-web/.next dinex-web/tsconfig.tsbuildinfo; find dinex -name __pycache__ -type d -prune -exec rm -rf {} +
