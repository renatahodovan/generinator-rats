=================================
*Generinator: RATS* Release Notes
=================================

18.2
====

* Use the *ANTLeRinator* package to automatically install the ANTLR packages
  (no need to run the install script manually anymore).
* Upgrade to ANTLR v4.7.1.
* Add parallelization both to the processor and to the generator.
* Refactor generator to be a callable context manager that can be directly used
  by *Fuzzinator* via API.
* Small fixes.


16.10
=====

First public release of the *Generinator: RATS* random test generator.

Summary of the main features:

* Extracting tags, attributes, and properties from html, svg, and css files
  using ANTLR v4.
* Generate new test cases using the extracted information.
* Install script to install the required ANTLR v4 framework.
