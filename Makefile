build:
	docker build -t registry.lan:5000/brigid/brigid:v0.93.1 .

push:
	docker push registry.lan:5000/brigid/brigid:v0.93.1
