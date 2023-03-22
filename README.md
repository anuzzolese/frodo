# FrODO
Frame-based Ontology Design Outlet (FrODO) is a novel method and Web tool for automatically drafting OWL ontologies from CQs. FrODO builds on and benefits from FRED [4] a machine reading [5] tool aimed at gathering RDF from text written in natural language. FRED in fact produces RDF graphs from text that are (i) domain- and task-independent, and (ii) designed according to the frame semantics [6] and ontology design patterns [7]. In essence, FrODO extends FRED specifically on the case of CQs by tailoring the RDF produced by FRED into domain ontologies. This is done by leveraging its formal representation based on the frame semantics. The domain ontologies produced by FrODO are drafts that can be used to feed agile ontology design methodologies. In this paper we demonstrate FrODO as a tool for generating domain ontologies formalised as OWL from competency questions automatically.

## Installation
FrODO requires Python 3. Once the source code has been downladed it is possible to install the Python package by means of pip. For example:
```
pip install .
```
Alternatively, it is possible to install the FrODO package directly from GitHub in the following way:
```
pip install git+https://github.com/anuzzolese/frodo
```
