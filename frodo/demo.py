from frodo import Frodo
import shortuuid
import webapp_conf


#shortuuid.set_alphabet("0123456789abcdefghijkmnopqrstuvwxyz")

sentence = 'What cars cost more than $50,000?'

namespace = ''.join([webapp_conf.NS, shortuuid.uuid(sentence)[:8], '/'])

frodo = Frodo(
    namespace=namespace,
    fred_uri=webapp_conf.FRED_ENDPOINT,
    fred_key=webapp_conf.FRED_KEY
)

#sentence = 'What are the contaminated sites in the area of Pavia recorded in 2020?'
#sentence = 'Who well commissioned a cultural property at a certain time?'
ontology = frodo.generate(sentence)
print(ontology.serialize(format='text/turtle'))