.PHONY: default build_ext clean docs

default: build_ext

build_ext:
	CC=mpicc CXX=mpic++ python setup.py build_ext 

clean:
	- rm -rf build
	- find ondacython/lib/ -name "*.so" -delete

docs:
	sphinx-apidoc -f -M -e  -o docs --separate onda onda/data_retrieval_layer/event_sources/hidra_api/ onda/data_retrieval_layer/event_sources/karabo_api/ onda/cfelpyutils
