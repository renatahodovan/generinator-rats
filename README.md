# Generinator: RATS
_Random Attributes, Tags & Style_

Random web content (HTML, CSS, SVG) generator for
[Fuzzinator](https://github.com/renatahodovan/fuzzinator).


## Requirements

* Python >= 3.4
* pip and setuptools Python packages (the latter is automatically installed by
  pip).
* MongoDB (either local installation or access to remote database)
* ANTLR v4


## Install

Clone the project and run setuptools:

    python setup.py install

(Quick pip install from PyPi will be available when ANTLR 4.5.4 is officially
released containing important fixes to the Python target and runtime.)

Once the project is installed, a helper script becomes available that downloads
the right version of the ANTLR v4 tool jar.

    generinator-rats-install-antlr4


## Usage

As a first step, *Generinator:RATS* needs to process existing web content to
extract names of, parent-child relation between, and values of tags and
attributes. The extracted information is then stored in a database.

Example invocation of the processing step:

    generinator-rats-process <input1.html> <input2.css> <input3.svg> <inputdir4>

Once the processing step has built a database, the generator of
*Generinator:RATS* can be used to produce any number of files with random web
content.

Example invocation of the generation step:

    generinator-rats -n <number-of-tests> -o <output-dir>

For more information on their usage, use the `--help` command line option on any
of the tools.

(Note: The processing step can be re-executed any number of times, even after
executing the generator. Actually, it may be really useful to periodically run
the processing step on new input files or test suites.)


## Copyright and Licensing

See [LICENSE](LICENSE.md).
