.PHONY: default build_ext clean

default: build_ext

build_ext:
	CC=mpicc CXX=mpic++ python setup.py build_ext 

clean:
	- rm -rf build
	- find ondacython/lib/ -name "*.so" -delete
