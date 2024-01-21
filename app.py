import os
import firebase_admin
from flask import Flask, render_template
from firebase_admin import credentials, firestore
if os.path.exists("env.py"):
    import env

# Create Flask app
app = Flask(__name__)

# Connect to Firestore DB
json_file_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
cred = credentials.Certificate(json_file_path)
firebase_admin.initialize_app(cred)

db = firestore.client()
db.collection("foods").add(
    {"img_url": "", 
     "is_processed":False})

@app.route("/")
def hello_world():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
                  debug=True)
