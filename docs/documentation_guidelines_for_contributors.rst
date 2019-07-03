Guidelines For Contributors
---------------------------

Version Control
---------------

OnDA is developed using the `Git <https://git-scm.com>` version control system.

OnDA uses the branching strategy proposed by Vincent Driessen and commonly known as
`Gitflow <https://nvie.com/posts/a-successful-git-branching-model>`.


Programming Languages
---------------------

Python
^^^^^^

OnDA is mainly developed in `Python  <https://www.python.org>`.

* All code in OnDA must run with both version 2 and 3 of Python, except for
  facility-specific code that specifically requires one of the two versions (for example,
  Python 2 for the LCSL facility). The code must specifically support the following
  versions of python:

  **Python 2**

  * 2.7

  **Python 3**

  * 3.4
  * 3.5
  * 3.6
  * 3.7

* The `python-future <https://python-future.org>`_ project should be used to ensure that
  code contributed to the OnDA project is compatible with all the supported versions of
  Python.

* The Python coding style should follow for the most part the `Google Python \
  Coding Style <https://github.com/google/styleguide/blob/gh-pages/pyguide.md>`_.

* All docstrings should be written following the `Google Style \
  <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

* `Pylint <https://www.pylint.org>`_ should be run on the code before
  submission, as stated in the Google Python Coding Style Guide. In the root
  folder of the OnDA repository, contributors can find  a 'pylintrc' file with
  the settings that should be applied when linting OnDA's code. Please see here
  how to use the pylintrc file:
  `Running Pylint \
  <http://pylint.pycqa.org/en/latest/user_guide/run.html?highlight=pylintrc>`_.


C/C++
^^^^^
Some extension to OnDA can, for performance reason, be written using the 
`C++ <https://en.wikipedia.org/wiki/C%2B%2B>`_ or 
`C <https://en.wikipedia.org/wiki/C_(programming_language)>`_ programming languages.

* All C++ code in OnDA should follow at most the C++98 ISO standard, and the code should
  be able to compile on a Linux RHEL6/CentOS6 platform using the development stack that
  comes with a standard installation of these systems.

* All C++ code in OnDA should follow at most the C99 ISO standard, and should the same
  restrictions regarding being able to compile on a Linux RHEL6/CentOS6 platform.

* The `Cython <http://cython.org>`_ project should be used to interface C/C++ code with
  Python.


