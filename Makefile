.PHONY: build_ext clean 

build_ext: 
	@if test -z "$$ONDA_CHEETAH_INCLUDE_DIR"; then echo Please set ONDA_CHEETAH_INCLUDE_DIR correctly; exit 1; fi
	@if test -z "$$ONDA_CHEETAH_LIBRARY_DIR"; then echo Please set ONDA_CHEETAH_LIBRARY_DIR correctly; exit 1; fi
	@if test -z "$$ONDA_INSTALLATION_DIR"; then echo Please set ONDA_INSTALLATION_DIR correctly; exit 1; fi
	@python setup.py build_ext

clean:
	@if [ -d "build" ] ; then rm -r build python_extensions ; fi 
	@if [ -d "python extensions" ] ; then rm -r python_extensions/*so; fi

