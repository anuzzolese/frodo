import re

from fredclient import FREDClient, FREDParameters, FREDDefaults
import nltk
from nltk.stem import WordNetLemmatizer
from rdflib import RDFS, RDF, OWL, URIRef, Literal, BNode, Graph, Namespace
from rdflib.paths import evalPath, OneOrMore

from abc import ABC, abstractmethod
from typing import List, Dict, NoReturn, Tuple


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
    def labelize_uriref(uriref: URIRef, lang: str = None, datatype: URIRef = None) -> Literal:
        
        ns = MorphUtils.get_namespace(uriref)
    
        uriref_str = str(uriref)
        term_id = uriref_str.replace(ns, '')

        
        
        label = term_id[0:1] + re.sub('([A-Z]{1})', r' \1', term_id[1:]).lower() 

        return Literal(label, lang) if lang else Literal(label, datatype) if datatype else Literal(label)

    @staticmethod
    def migrate_taxonomy(g: Graph, source_cls: URIRef, target_cls: URIRef) -> NoReturn:

        ontology = Graph()
        ns = MorphUtils.get_namespace(target_cls)
        print(f"Subclass {source_cls}")
        for subclass in g.objects(source_cls, RDFS.subClassOf):
            if str(subclass).startswith(FREDDefaults.DEFAULT_FRED_NAMESPACE):
                sc = URIRef(str(subclass).replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, ns))
                ontology.add((target_cls, RDFS.subClassOf, sc))
                ontology.add((sc, RDF.type, OWL.Class))

                label = MorphUtils.labelize_uriref(sc, 'en')
                ontology.add((sc, RDFS.label, label))
                ontology += MorphUtils.migrate_taxonomy(g, subclass, sc)

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
        term_iri = str(term)
        class_label = term_iri.replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
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
            SELECT ?subj ?subjtype ?rel ?obj ?objtype
            WHERE{{
                ?subj ?rel ?obj;
                    a ?subjtype .
                ?obj a ?objtype
                OPTIONAL{{ 
                    ?type rdfs:subClassOf ?subtype .
                    ?subtype rdfs:subClassOf* dul:Event}}
                FILTER(!BOUND(?subtype))
                FILTER(REGEX(STR(?rel), '{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                FILTER(REGEX(STR(?subjtype), '{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                FILTER(REGEX(STR(?objtype), '{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
            }}
            '''
        resultset = g.query(sparql)
        for row in resultset:
            subj = row.subj
            subjtype = row.subjtype
            binary_predicate = row.rel
            obj = row.obj
            objtype = row.objtype

            subjtype_iri = str(subjtype)
            objtype_iri = str(objtype)
            binary_predicate_iri = str(binary_predicate)

            object_id = objtype_iri.replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')

            subject_class = URIRef(self._ns + subjtype_iri.replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, ''))
            ontology.add((subject_class, RDF.type, OWL.Class))
            ontology.add((subject_class, RDFS.label, MorphUtils.labelize_uriref(subject_class, 'en')))
            ontology += MorphUtils.migrate_taxonomy(g, subjtype, subject_class)
            
            object_class = URIRef(self._ns + object_id)
            ontology.add((object_class, RDF.type, OWL.Class))
            ontology.add((object_class, RDFS.label, MorphUtils.labelize_uriref(object_class, 'en')))
            ontology += MorphUtils.migrate_taxonomy(g, objtype, object_class)

            object_property = URIRef("".join([self._ns, binary_predicate_iri.replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, ''), object_id]))
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
            SELECT ?situation ?situationtype
            WHERE{{
                ?situation a ?situationtype .
                ?situationtype rdfs:subClassOf+ dul:Event
                FILTER(REGEX(STR(?situation), '{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
                FILTER(REGEX(STR(?situationtype), '{FREDDefaults.DEFAULT_FRED_NAMESPACE}'))
            }}
            '''
        resultset = g.query(sparql)

        #paths = evalPath(g, (None, RDF.type/(RDFS.subClassOf*OneOrMore), URIRef('http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Event')))
        #for path in paths:
        for row in resultset:
            situation = row.situation
            situation_type = row.situationtype
            
            situation_iri = str(situation)
        
            
            predicates = {
                'passive-roles': [],
                'agentive-roles': [],
                'conditional-agentive-roles': [],
                'oblique-roles': [],
                'fred-roles': []
            }
            
            for p in g.predicates(subject=situation):
                p_iri = str(p)
                if p_iri in FREDDefaults.ROLES['passive']:
                    predicates['passive-roles'].append(p)
                elif p_iri in FREDDefaults.ROLES['agentive']:
                    predicates['agentive-roles'].append(p)
                elif p_iri in FREDDefaults.ROLES['conditional_agentive']:
                    predicates['conditional-agentive-roles'].append(p)
                elif p_iri in FREDDefaults.ROLES['oblique']:
                    predicates['oblique-roles'].append(p)
                elif p_iri.startswith(FREDDefaults.DEFAULT_FRED_NAMESPACE):
                    predicates['fred-roles'].append(p)

            situation_digest = {
                    'id': situation,
                    'situation-type': situation_type,
                    'passive-roles': [],
                    'agentive-roles': [],
                    'conditional-agentive-roles': [],
                    'oblique-roles': [],
                    'fred-roles': []
            }

            flag = False
            for role_type in ['passive-roles', 'agentive-roles', 'conditional-agentive-roles', 'oblique-roles', 'fred-roles']:
                tmp_situation_digest = self.__browse_situation_branch(g, situation, situation_type, predicates[role_type], role_type)
                situation_digest.update({role_type: tmp_situation_digest[role_type]})
                if not flag:

                    '''
                    Here we transform the class label derived from a frame into a gerundive form.
                    '''
                    
                    class_label = tmp_situation_digest['class-label']
                    
                    event_target = URIRef(self._ns + class_label)
                    
                    ontology += MorphUtils.migrate_taxonomy(g, situation_type, event_target)
                    
                    class_label_terms = class_label[0:1] + re.sub('([A-Z]{1})', r' \1', class_label[1:])
                    class_label_terms = class_label_terms.split()
                    gerundive = self.__lemmatizer.lemmatize(class_label_terms[-1], 'v') + 'ing'
                    gerundive = gerundive[0:1].upper() + gerundive[1:]

                    class_label = "".join(class_label_terms[:-1]) + gerundive
                    situation_digest.update({'class-label': class_label})
                    
                    flag = True
                    
        
            for role_type in ['passive-roles', 'agentive-roles', 'conditional-agentive-roles', 'oblique-roles', 'fred-roles']:
                ontology = self.__formalise(g, situation_digest, role_type, ontology)


            
        return ontology

    def __browse_situation_branch(self, g: Graph, situation: URIRef, situation_type: URIRef, roles: List[URIRef], role_type) -> Dict:
        situation_digest = {
            'id': situation,
            'passive-roles': [],
            'agentive-roles': [],
            'conditional-agentive-roles': [],
            'oblique-roles': [],
            'fred-roles': [],
            'class-label': None
        }
        class_label = str(situation_type).replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')

        for role in roles:
            for actor in g.objects(situation, role/RDF.type):
                actor_iri = str(actor)
                if actor_iri.startswith(FREDDefaults.DEFAULT_FRED_NAMESPACE) or actor == OWL.Thing:
                    
                    local_class_id = actor_iri.replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')

                    ontology_class = URIRef(self._ns + local_class_id)
                    situation_digest[role_type].append({'role': role, 'actor': ontology_class, 'fred-class': actor})

                    class_label = local_class_id + class_label if actor != OWL.Thing else class_label 
        
        situation_digest.update({'class-label': class_label})
        
        return situation_digest

    def __formalise(self, g: Graph, situation_digest: Dict, roles_type: str, ontology: Graph) -> Graph:
        
        class_iri = URIRef(self._ns+situation_digest['class-label'])

        ontology.add((class_iri, RDF.type, OWL.Class))
        ontology.add((class_iri, RDFS.label, MorphUtils.labelize_uriref(class_iri, 'en')))


        fred_situation_type = situation_digest['situation-type']
        gerund = MorphUtils.gerundify(fred_situation_type)
        gerundive_res = URIRef("".join([self._ns, gerund]))
        ontology.add((gerundive_res, RDF.type, OWL.Class))
        ontology.add((gerundive_res, RDFS.label, MorphUtils.labelize_uriref(gerundive_res)))
        ontology.add((class_iri, RDFS.subClassOf, gerundive_res))
                    
        
        roles = situation_digest[roles_type]
        for role in roles:
            role_predicate = role['role']
            role_actor = role['actor']
            fred_class = role['fred-class']
            
            role_actor_iri = str(role_actor)

            if roles_type == 'fred-roles':
                role_id = str(role_actor_iri).replace(self._ns, '').replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
                predicate_id = str(role_predicate).replace(self._ns, '').replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
                predicate = URIRef(''.join([self._ns, predicate_id, role_id]))
            else:
                predicate_id = str(role_actor_iri).replace(self._ns, '').replace(FREDDefaults.DEFAULT_FRED_NAMESPACE, '')
                predicate = URIRef(''.join([self._ns, 'involves', predicate_id]))
            
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
            ontology += MorphUtils.migrate_taxonomy(g, fred_class, role_actor)
        
        return ontology

class CQOntoGen:

    def __init__(self, namespace, fred_uri: str, morphisms: Tuple[MorphismI] = None):
        self.__g: Graph = None
        self.__ns: str = namespace
        self.__fred_uri = fred_uri
        self.__morphisms: Tuple[MorphismI] = morphisms if morphisms else (BinaryRelationMorphism(namespace), NAryRelationMorphism(namespace))

    def get_namespace() -> str:
        return self.__ns

    def set_namesapce(namespace: str):
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

        
