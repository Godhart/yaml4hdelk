.PHONY: sketch general operators afifo

sketch:
	python ../yaml4schm.py sketch.yaml html/d3hw-sketch.html
	python ../yaml4schm.py sketch.yaml html/hdelk-sketch.html -t hdelk

general:
	python ../yaml4schm.py top.yaml html/d3hw-top.html
	python ../yaml4schm.py top.yaml html/hdelk-top.html -t hdelk

	python ../yaml4schm.py top_d.yaml html/d3hw-top_d.html
	python ../yaml4schm.py top_d.yaml html/hdelk-top_d.html -t hdelk

	python ../yaml4schm.py unit1.yaml html/d3hw-unit1.html
	python ../yaml4schm.py unit1.yaml html/hdelk-unit1.html -t hdelk

	python ../yaml4schm.py unit2.yaml html/d3hw-unit2.html
	python ../yaml4schm.py unit2.yaml html/hdelk-unit2.html -t hdelk

operators:
	python ../yaml4schm.py operators.yaml html/d3hw-operators.html

afifo:
	python ../yaml4schm.py afifo.yaml html/d3hw-afifo.html
	python ../yaml4schm.py afifo.yaml html/hdelk-afifo.html -t hdelk -s

all: sketch general operators afifo
