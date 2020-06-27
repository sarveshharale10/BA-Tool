from pymongo import MongoClient
from flask import Flask,jsonify, render_template, request, redirect,json, session, Response
from api import api
from api.routes import get_monitors,get_alerts,top_holders,top_receivers,top_senders
from migration_scripts.db_syncer import *

from passlib.hash import sha256_crypt

from hashlib import sha256

def isUserLoggedIn():
	if 'logged_in' not in session or session['logged_in'] == False:
		session['logged_in'] == False
		return False
	else:
		return True

'''
var mapFunction3 = function() {
    this.outputs.forEach(function(item){ emit(item.address,+item.amount); });
	this.inputs.forEach(function(item){ emit(item.address,-item.amount); });
}

var reduceFunction3 = function(address,amounts) {
                          return Array.sum(amounts);
                      };
db.alerts.aggregate({
"$lookup":{
     from: 'transactions',
     localField: 'tx_hash',
     foreignField: 'tx_hash',
     as: 'details'
}
});
'''
def init_page():
	if 'logged_in' not in session:
		session['logged_in'] = False
	responses = get_alerts(app.config["db"])

	settings = {"db":app.config["db_name"],"limit":app.config["limit"], "alerts":responses, "logged_in":session['logged_in'] }
	return settings
	



app = Flask(__name__)
app.config["db_name"] = "ba"
app.config["db"] = MongoClient("mongodb://localhost:27017")[app.config["db_name"]]
app.config["limit"] = 100
app.config["syncer"] = {
	"ba":BtcDBSyncer(),
	"vjcoin":VjCoinDbSyncer()
}
app.secret_key = 'ba_tool'
app.register_blueprint(api)



def hash_password(password):
    # return sha256_crypt.hash(password)
    return sha256(password.encode()).hexdigest()

@app.route("/settings",methods=['POST'])
def setting():
	# print(request.values)
	db = request.values["db"]
	limit = request.values["limit"]
	app.config["db_name"] = db
	app.config["db"] = MongoClient("mongodb://localhost:27017")[db]
	app.config["limit"] = int(limit)

	return jsonify({'success':1})

@app.route("/test",methods=['GET'])
def test():
	settings = init_page()
	return render_template('test.html',config=settings)

@app.route("/track",methods=['GET'])
def track():
	settings = init_page()
	return render_template('track.html',config=settings)

@app.route("/trace", methods=['GET'])
def trace():
	settings = init_page()
	return render_template('trace.html',config=settings)

@app.route("/", methods=['GET'])
def home():
	session['logged_in'] = False
	return redirect("/home")

@app.route("/home", methods=['GET','POST'])
def dashboard():
	holders = top_holders()
	receivers = top_receivers()
	senders = top_senders()
	settings = init_page()
	return render_template("index.html",holders=holders,senders=senders,receivers=receivers,config=settings)

@app.route("/search", methods=['GET'])
def search():
	settings = init_page()
	return render_template("search.html",config=settings)

@app.route("/alerts", methods=['GET','POST'])
def alert():
	settings = init_page()
	db = app.config["db"]
	return render_template("alerts.html",config=settings)

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'GET':
		response = Response(render_template('login.html'))
		response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')   
		return response
	else:

		email = request.form['email']
		password = hash_password(request.form['password'])

		client = MongoClient("mongodb://localhost:27017")
		ba = client["users"]
		users = ba["users"]

		count = users.count({"email":email})
		
		if count > 0:
			result = users.find({"email":email})[0]
			print(result)
			if result['password'] == password:
				session['logged_in'] = True
				session['id'] = str(result['_id'])
				return '1'
		# user.insert(document)
		return '0'

@app.route('/signup', methods=['GET', 'POST'])
def register():
	if request.method == 'GET':
		return render_template('signup.html')
	else:
		email = request.form['email']
		password = hash_password(request.form['password'])

		client = MongoClient("mongodb://localhost:27017")
		ba = client["users"]
		users = ba["users"]

		result = users.find({"email":email}).count()
		if result > 0:
			return '2'
		document = {
			"email":email,
			"password":password
		}
		users.insert(document)
		return '1'


@app.route("/monitors", methods=['GET'])
def monitors():
	settings = init_page()
	db = app.config["db"]
	responses = get_monitors(db)
	return render_template("monitors.html",config=settings,responses=responses)

@app.route("/logout",methods=['POST'])
def logout():
	session.clear()
	session['logged_in']=False
	return jsonify({'success':1})

@app.after_request
def add_header(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)