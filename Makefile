IMAGE_ODOO:=quay.io/opsway/odoo:opsway

all: build push

build:
	docker build --pull -t ${IMAGE_ODOO} .

push:
	docker push ${IMAGE_ODOO}

add-checks:
	pip3 install  --break-system-packages -r requirements-lint.txt && pre-commit install

remove-checks:
	pre-commit uninstall
