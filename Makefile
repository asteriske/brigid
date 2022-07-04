build:
	docker build -t registry.lan:5000/brigid:latest .

push:
	docker image push registry.lan:5000/brigid:latest
