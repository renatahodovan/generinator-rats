=================
Generinator: RATS
=================
*Random Attributes, Tags & Style*

Random web content (HTML, CSS, SVG) generator for
Fuzzinator_.

.. _Fuzzinator: https://github.com/renatahodovan/fuzzinator

Requirements
============

* Python_ >= 3.5
* pip_ and setuptools Python packages (the latter is automatically installed by
  pip).
* MongoDB_ (either local installation or access to remote database)
* ANTLR_ v4

.. _Python: https://www.python.org
.. _pip: https://pip.pypa.io
.. _MongoDB: https://www.mongodb.com/
.. _ANTLR: http://www.antlr.org

Install
=======

The quick way::

    pip install generinator-rats

Alternatively, by cloning the project and running setuptools::

    python setup.py install


Usage
=====

As a first step, *Generinator:RATS* needs to process existing web content to
extract names of, parent-child relation between, and values of tags and
attributes. The extracted information is then stored in a database.

Example invocation of the processing step::

    generinator-rats-process <input1.html> <input2.css> <input3.svg> <inputdir4>

Once the processing step has built a database, the generator of
*Generinator:RATS* can be used to produce any number of files with random web
content.

Example invocation of the generation step::

    generinator-rats -n <number-of-tests> -o <output-dir>

For more information on their usage, use the `--help` command line option on any
of the tools.

(Note: The processing step can be re-executed any number of times, even after
executing the generator. Actually, it may be really useful to periodically run
the processing step on new input files or test suites.)


Copyright and Licensing
=======================

See LICENSE_.

.. _LICENSE: LICENSE.rst
