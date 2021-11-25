import re

from fredclient import FREDClient, FREDParameters, FREDDefaults
import nltk
from nltk.stem import WordNetLemmatizer
from rdflib import RDFS, RDF, OWL, XSD, URIRef, Literal, BNode, Graph, Namespace
from rdflib.paths import evalPath, OneOrMore

from abc import ABC, abstractmethod
from typing import List, Dict, NoReturn, Tuple
from rdflib.term import URIRef


nltk.download('wordnet')

class MorphUtils:

    LEMMATIZER: WordNetLemmatizer = WordNetLemmatizer()
        
    @staticmethod
    def get_namespace(uriref: URIRef) -> str:
        uriref_str = str(uriref)
        last_hash = uriref_str.rfind('#')
        last_slash = uriref_str.rfind('/')

        return uriref_str[:last_hash+1] if last_hash > last_slash else uriref_str[:last_slash+1]
    
    @staticmethod
    def get_id(uriref: URIRef) -> str:
        uriref_str = str(uriref)
        last_hash = uriref_str.rfind('#')
        last_slash = uriref_str.rfind('/')

        return uriref_str[last_hash+1:] if last_hash > last_slash else uriref_str[last_slash+1:]

    @staticmethod
    def labelize_uriref(uriref: URIRef, lang: str = None, datatype: URIRef = None) -> Literal:
        
        ns = MorphUtils.get_namespace(uriref)
    
        uriref_str = str(uriref)
        term_id = uriref_str.replace(ns, '')

        
        
        label = term_id[0:1] + re.sub('([A-Z]{1})', r' \1', term_id[1:]).lower() 

        return Literal(label, lang) if lang else Literal(label, datatype) if datatype else Literal(label)

    @staticmethod
    def migrate_taxonomy(g: Graph, source_cls: URIRef, target_cls: URIRef, gerundify: bool = False, predicate: URIRef = RDFS.subClassOf) -> NoReturn:
        
        ontology = Graph()
        ns = MorphUtils.get_namespace(target_cls)
        for subclass in g.objects(source_cls, predicate):
            if str(subclass).startswith(FREDDefaults.DEFAULT_FRED_NAMESPACE):
                if gerundify:
                    sc = URIRef(ns + MorphUtils.gerundify(subclass))
                else:
                    sc = URIRef(ns + MorphUtils.get_id(subclass))
                ontology.add((target_cls, RDFS.subClassOf, sc))
                ontology.add((sc, RDF.type, OWL.Class))

                label = MorphUtils.labelize_uriref(sc, 'en')
                ontology.add((sc, RDFS.label, label))
                ontology += MorphUtils.migrate_taxonomy(g, subclass, sc, gerundify)

        return ontology

    @staticmethod
    def inverse(predicate: URIRef) -> URIRef:
        ns = MorphUtils.get_namespace(predicate)
        predicate_id = predicate.replace(ns, '')

        add_of = False
        if predicate_id.startswith('involves'):
            predicate_id = predicate_id.replace('involves', '') + 'InvolvedIn'
        else:
            add_of = True
            
        inverse_predicate_id = 'is' + predicate_id[0:1].upper() + predicate_id[1:]
        
        if add_of:
            inverse_predicate_id += 'Of'

        return URIRef(ns + inverse_predicate_id)

    
    @staticmethod
    def gerundify(term: URIRef) -> Graph:
        class_label = MorphUtils.get_id(term)
        class_label_terms = class_label[0:1] + re.sub('([A-Z]{1})', r' \1', class_label[1:])
        class_label_terms = class_label_terms.split()
        gerundive = MorphUtils.LEMMATIZER.lemmatize(class_label_terms[-1], 'v') + 'ing'
        gerundive = gerundive[0:1].upper() + gerundive[1:]

        return "".join(class_label_terms[:-1]) + gerundive
        

class MorphismI(ABC):

    def __init__(self, ns: Namespace):
        self._ns = ns

    @abstractmethod
    def morph(self, g: Graph) -> Graph:
        pass
        

class BinaryRelationMorphism(MorphismI):
    
    def morph(self, g: Graph) -> Graph:

        ontology = Graph()

        sparql = f'''
            PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
            PREFIX owl: <{OWL._NS}>
            SELECT ?subj ?subjtype ?subjsameastype ?rel ?obj ?objtype ?objsameastype
            WHERE{{
                ?subj ?rel ?obj
                OPTIONAL{{
                    ?subj a ?subjtype
                    FILTER(REGEX(STR(?subjtype), '^{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                }}
                OPTIONAL{{
                    ?obj a ?objtype
                    FILTER(REGEX(STR(?objtype), '^{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                }}
                OPTIONAL{{
                    ?subj owl:sameAs/rdf:type ?subjsameastype
                }}
                OPTIONAL{{
                    ?obj owl:sameAs/rdf:type ?objsameastype
                }}
                OPTIONAL{{ 
                    ?subjtype rdfs:subClassOf ?subtype .
                    ?subtype rdfs:subClassOf* dul:Event}}
                FILTER(!BOUND(?subtype))
                FILTER(REGEX(STR(?rel), '^{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
            }}
            '''
        
        resultset = g.query(sparql)
        for row in resultset:
            subjtype = row.subjtype
            subjsameastype = row.subjsameastype
            binary_predicate = row.rel
            objtype = row.objtype
            objsameastype = row.objsameastype

            if subjtype:
                subj = subjtype
            elif subjsameastype:
                subj = subjsameastype
            else:
                subj = None
                
            if objtype:
                obj = objtype
            elif objsameastype:
                obj = objsameastype
            else:
                obj = None
                
            if subj and obj:
                
                subject_id = MorphUtils.get_id(subj)
                predicate_id = MorphUtils.get_id(binary_predicate)
                object_id = MorphUtils.get_id(obj)
    
                subject_class = URIRef(self._ns + subject_id)
                ontology.add((subject_class, RDF.type, OWL.Class))
                ontology.add((subject_class, RDFS.label, MorphUtils.labelize_uriref(subject_class, 'en')))
                ontology += MorphUtils.migrate_taxonomy(g, subj, subject_class)
                
                object_class = URIRef(self._ns + object_id)
                ontology.add((object_class, RDF.type, OWL.Class))
                ontology.add((object_class, RDFS.label, MorphUtils.labelize_uriref(object_class, 'en')))
                ontology += MorphUtils.migrate_taxonomy(g, obj, object_class)
    
                object_property = URIRef("".join([self._ns, predicate_id, object_id]))
                ontology.add((object_property, RDF.type, OWL.ObjectProperty))
                ontology.add((object_property, RDFS.domain, OWL.Thing))
                ontology.add((object_property, RDFS.range, object_class))
                ontology.add((object_property, RDFS.label, MorphUtils.labelize_uriref(object_property, 'en')))
    
    
                inverse_object_property = MorphUtils.inverse(object_property)
                ontology.add((inverse_object_property, RDF.type, OWL.ObjectProperty))
                ontology.add((inverse_object_property, RDFS.domain, object_class))
                ontology.add((inverse_object_property, RDFS.range, OWL.Thing))
                ontology.add((inverse_object_property, RDFS.label, MorphUtils.labelize_uriref(inverse_object_property, 'en')))
    
                restriction = BNode()
    
                ontology.add((restriction, RDF.type, OWL.Restriction))
                ontology.add((restriction, OWL.onProperty, object_property))
                ontology.add((restriction, OWL.someValuesFrom, object_class))
                ontology.add((subject_class, RDFS.subClassOf, restriction))

        return ontology
    
class RoleType:
    
    PASSIVE = 'PASSIVE'
    AGENTIVE = 'AGENTIVE'
    CONDITIONAL_AGENTIVE = 'CONDITIONAL_AGENTIVE'
    OBLIQUE = 'OBLIQUE'
    FRED_ROLE = 'FRED_ROLE'
    
    @staticmethod
    def get_role_type(role: URIRef):
        
        role = str(role)
        role_type = None
        if role in FREDDefaults.ROLES['passive']:
            role_type = RoleType.PASSIVE
        elif role in FREDDefaults.ROLES['agentive']:
            role_type = RoleType.AGENTIVE
        elif role in FREDDefaults.ROLES['conditional_agentive']:
            role_type = RoleType.CONDITIONAL_AGENTIVE
        elif role in FREDDefaults.ROLES['oblique']:
            role_type = RoleType.OBLIQUE
        elif role.startswith(FREDDefaults.DEFAULT_FRED_NAMESPACE):
            role_type = RoleType.FRED_ROLE
            
        return role_type


class RoleMap:
    
    def __init__(self, role: URIRef, ontology_class: URIRef, fred_class: URIRef, role_type: str):
        self.__role = role
        self.__ontology_class = ontology_class
        self.__fred_class = fred_class
        self.__role_type = role_type
        
    def get_role(self) -> URIRef:
        return self.__role
    
    def get_ontology_class(self) -> URIRef:
        return self.__ontology_class
    
    def get_fred_class(self) -> URIRef:
        return self.__fred_class
    
    def get_role_type(self) -> str:
        return self.__role_type

    
class SituationDigest:


    def __init__(self, source_graph: Graph, situation: URIRef, situation_type: URIRef):
        self.__source_graph = source_graph
        self.__situation = situation
        self.__situation_type = situation_type
        self.__passive_roles: List[RoleMap] = []
        self.__agentive_roles: List[RoleMap] = []
        self.__conditional_agentive_roles: List[RoleMap] = []
        self.__oblique_roles: List[RoleMap] = []
        self.__fred_roles: List[RoleMap] = []
        self.__class_label: str = None
        
    def get_source_graph(self) -> Graph:
        return self.__source_graph    
    
    def get_situation(self) -> URIRef:
        return self.__situation
    
    def get_situation_type(self) -> URIRef:
        return self.__situation_type
        
    def add_role_map(self, participant: URIRef, role_type: str):
        if role_type == RoleType.AGENTIVE:
            self.__agentive_roles.append(participant)
        elif role_type == RoleType.PASSIVE:
            self.__passive_roles.append(participant)
        elif role_type == RoleType.CONDITIONAL_AGENTIVE:
            self.__conditional_agentive_roles.append(participant)
        elif role_type == RoleType.OBLIQUE:
            self.__oblique_roles.append(participant)
        elif role_type == RoleType.FRED_ROLE:
            self.__fred_roles.append(participant)
            
    def get_participants_of_role_type(self, role_type: str) -> str:
        
        participants = None
        if role_type == RoleType.AGENTIVE:
            participants = self.__agentive_roles
        elif role_type == RoleType.PASSIVE:
            participants = self.__passive_roles
        elif role_type == RoleType.CONDITIONAL_AGENTIVE:
            participants = self.__conditional_agentive_roles
        elif role_type == RoleType.OBLIQUE:
            participants = self.__oblique_roles
        elif role_type == RoleType.FRED_ROLE:
            participants = self.__fred_roles
            
        return participants
    
    def get_class_label(self) -> str:
        return self.__class_label
    
    def set_class_label(self, class_label: str):
        
        self.__class_label = class_label
    
    def update_class_label(self, class_label: str):
        
        if not self.__class_label:
            self.__class_label = ''
             
        self.__class_label = class_label + self.__class_label
        
        
    def formalise(self, namespace: str) -> Graph:
        
        ontology = Graph()
        
        class_iri = URIRef(namespace+self.__class_label)

        ontology.add((class_iri, RDF.type, OWL.Class))
        ontology.add((class_iri, RDFS.label, MorphUtils.labelize_uriref(class_iri, 'en')))
        
        ontology += MorphUtils.migrate_taxonomy(self.__source_graph, self.__situation, class_iri, True, RDF.type)

        '''
        fred_situation_type = self.__situation_type
        gerund = MorphUtils.gerundify(fred_situation_type)
        gerundive_res = URIRef("".join([namespace, gerund]))
        ontology.add((gerundive_res, RDF.type, OWL.Class))
        ontology.add((gerundive_res, RDFS.label, MorphUtils.labelize_uriref(gerundive_res)))
        ontology.add((class_iri, RDFS.subClassOf, gerundive_res))
        '''
        
        role_maps: List[RoleMap] = [*self.__agentive_roles, *self.__passive_roles, *self.__conditional_agentive_roles, *self.__oblique_roles, *self.__fred_roles]
        
        for role_map in role_maps:
            role_predicate = role_map.get_role()
            role_actor = role_map.get_ontology_class()
            fred_class = role_map.get_fred_class()
            role_type = role_map.get_role_type()
            
            role_actor_iri = str(role_actor)

            if role_type == RoleType.FRED_ROLE:
                role_id = str(role_actor_iri).replace(namespace, '').replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
                predicate_id = str(role_predicate).replace(namespace, '').replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
                predicate = URIRef(''.join([namespace, predicate_id, role_id]))
            else:
                predicate_id = str(role_actor_iri).replace(namespace, '').replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
                predicate = URIRef(''.join([namespace, 'involves', predicate_id]))
            
            ontology.add((predicate, RDF.type, OWL.ObjectProperty))
            ontology.add((predicate, RDFS.label, MorphUtils.labelize_uriref(predicate)))

            restriction = BNode()

            ontology.add((restriction, RDF.type, OWL.Restriction))
            ontology.add((restriction, OWL.onProperty, predicate))
            ontology.add((restriction, OWL.someValuesFrom, role_actor))
            ontology.add((class_iri, RDFS.subClassOf, restriction))

            ontology.add((predicate, RDFS.domain, OWL.Thing))
            ontology.add((predicate, RDFS.range, role_actor))

            # Inverse predicate
            inverse_predicate = MorphUtils.inverse(predicate)
            ontology.add((inverse_predicate, RDF.type, OWL.ObjectProperty))
            ontology.add((inverse_predicate, RDFS.label, MorphUtils.labelize_uriref(inverse_predicate)))
            ontology.add((inverse_predicate, RDFS.domain, role_actor))
            ontology.add((inverse_predicate, RDFS.range, OWL.Thing))
            ontology.add((inverse_predicate, OWL.inverseOf, predicate))
            ontology.add((predicate, OWL.inverseOf, inverse_predicate))

            ontology.add((role_actor, RDF.type, OWL.Class))
            ontology.add((role_actor, RDFS.label, MorphUtils.labelize_uriref(role_actor)))
            
            ontology += MorphUtils.migrate_taxonomy(self.__source_graph, fred_class, role_actor)
        
        return ontology
    

class NAryRelationMorphism(MorphismI):

    def __init__(self, ns):
        super().__init__(ns)
        self.__lemmatizer: WordNetLemmatizer = WordNetLemmatizer()
    
    
    def morph(self, g: Graph) -> Graph:

        ontology = Graph()

        '''
        We first detect frame occurrences for the base case.
        Frame occurrences are detected by querying the graph with the following property path:
        ?x rdf:type/rdfs:subClassOf* dul:Event
        '''

        sparql = f'''
            PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
            PREFIX owl: <{OWL._NS}>
            PREFIX xsd: <{XSD._NS}>
            SELECT ?situation ?situationtype ?role ?participant ?participanttype ?participantsameastype
            WHERE{{
                ?situation a ?situationtype ;
                    ?role ?participant .
                OPTIONAL{{
                    ?participant a ?participanttype
                    FILTER(REGEX(STR(?participanttype), '^{FREDDefaults.DEFAULT_FRED_NAMESPACE}') || ?participanttype = owl:Thing)
                }}
                OPTIONAL{{
                    {{?participant owl:sameAs/a ?participantsameastype}}
                    UNION
                    {{
                    ?situation ?role2 ?participant2
                    FILTER(datatype(?participant2) = xsd:date || datatype(?participant2) = xsd:dateTime)
                    BIND(dul:Time AS ?participantsameastype)
                    }}
                }}
                ?situationtype rdfs:subClassOf+ dul:Event
                FILTER(REGEX(STR(?situation), '^{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                FILTER(REGEX(STR(?situationtype), '^{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                FILTER(REGEX(STR(?role), '^http://www.ontologydesignpatterns.org/ont/') )
            }}
            '''
        resultset = g.query(sparql)

        #paths = evalPath(g, (None, RDF.type/(RDFS.subClassOf*OneOrMore), URIRef('http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Event')))
        #for path in paths:
        
        situations_registry: Dict[URIRef, SituationDigest] = dict()
        
        for row in resultset:
            situation = row.situation
            situation_type = row.situationtype
            
            role = row.role
            
            role_type = RoleType.get_role_type(role)
            
            if row.participanttype:
                participant_type = row.participanttype
            elif row.participantsameastype:
                participant_type = row.participantsameastype
            else:
                participant_type = None
                
            if participant_type and role_type:
                
                if situation in situations_registry:
                    situation_digest = situations_registry[situation]
                else:
                    situation_digest = SituationDigest(g, situation, situation_type)
                    situations_registry.update({situation: situation_digest})
                    
                    situation_digest.set_class_label(MorphUtils.gerundify(situation_type))
                    
                local_class_id = MorphUtils.get_id(participant_type)
                ontology_class = URIRef(self._ns + local_class_id)
                
                role_map = RoleMap(role, ontology_class, participant_type, role_type)
                
                situation_digest.add_role_map(role_map, role_type)
                
                if role_type == RoleType.PASSIVE:
                    situation_digest.update_class_label(local_class_id)
                
                
        for situation, digest in situations_registry.items():
            ontology += digest.formalise(self._ns)
            
        return ontology
    

class Frodo:

    def __init__(self, namespace, fred_uri: str, morphisms: Tuple[MorphismI] = None):
        self.__g: Graph = None
        self.__ns: str = namespace
        self.__fred_uri = fred_uri
        self.__morphisms: Tuple[MorphismI] = morphisms if morphisms else (BinaryRelationMorphism(namespace), NAryRelationMorphism(namespace))

    def get_namespace(self) -> str:
        return self.__ns

    def set_namesapce(self, namespace: str):
        self.__ns = namespace
        
    def generate(self, cq: str) -> Graph:
        
        
        fredclient = FREDClient(self.__fred_uri)
        self.__g = fredclient.execute_request(cq, FREDParameters(semantic_subgraph=False))
        ontology = Graph()
        ontology.add((URIRef(self.__ns), RDF.type, OWL.Ontology))
        ontology.bind("owl", Namespace('http://www.w3.org/2002/07/owl#'))
        ontology.bind("rdf", Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#'))
        ontology.bind("rdfs", Namespace('http://www.w3.org/2000/01/rdf-schema#'))
        ontology.bind("", Namespace(self.__ns))

        for morphism in self.__morphisms:
            ontology += morphism.morph(self.__g)

        return ontology

        
