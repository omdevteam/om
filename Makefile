.PHONY: default build_ext clean docs

default: build_ext

build_ext:
	python setup.py build_ext --inplace

clean:
	- rm -rf build
	- find onda/algorithms/peakfinder8_extension -name "peakfinder8_extension*.so" -delete

docs:
	sphinx-apidoc -f -M -e -o docs --separate onda onda/data_retrieval_layer/event_sources/hidra_api/ onda/data_retrieval_layer/event_sources/karabo_api/
