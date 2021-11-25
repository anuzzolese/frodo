from flask import Flask, Response, render_template, request
from frodo import Frodo
import shortuuid


shortuuid.set_alphabet("0123456789abcdefghijkmnopqrstuvwxyz")

myapp = Flask(__name__)

FRED_ENDPOINT = ''
NS = 'https://w3id.org/stlab/ontology/'

@myapp.route("/")
def index():
    text = request.args.get("text")
    if text:
        
        namespace = ''.join([NS, shortuuid.uuid(text)[:8], '/'])
        frodo = Frodo(namespace, FRED_ENDPOINT)
        ontology = frodo.generate(text)
        return Response(ontology.serialize(format='text/turtle'),
            mimetype='text/turtle',
            headers={"Content-disposition":
                 "attachment; filename=ontology.ttl"})
    else:
        return render_template("index.html")

if __name__ == '__main__':	
    myapp.run()
