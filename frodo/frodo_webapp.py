from flask import Flask, Response, render_template, request
from frodo import Frodo
import shortuuid
import webapp_conf

myapp = Flask(__name__)

@myapp.route("/")
def index():
    text = request.args.get("text")
    if text:
        print(text)
        namespace = ''.join([webapp_conf.NS, shortuuid.uuid(text)[:8], '/'])
        frodo = Frodo(namespace, webapp_conf.FRED_ENDPOINT)
        ontology = frodo.generate(text)
        return Response(ontology.serialize(format='text/turtle'),
            mimetype='text/turtle',
            headers={"Content-disposition":
                 "attachment; filename=ontology.ttl"})
    else:
        return render_template("index.html", basepath=webapp_conf.BASEPATH)

if __name__ == '__main__':	
    myapp.run(port=webapp_conf.PORT)
