import os
import firebase_admin
from werkzeug.utils import secure_filename
from firebase_admin import credentials, firestore, storage
from authlib.integrations.flask_client import OAuth
from flask import Flask, render_template, redirect, url_for, session, request
if os.path.exists("env.py"):
    import env

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    authorize_params={
        'scope': 'openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
        'response_type': 'code'
    },
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'token_endpoint_auth_method': 'client_secret_post'}
)

# Connect to Firestore DB
json_file_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
cred = credentials.Certificate(json_file_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': os.environ.get("STORAGE_BUCKET")
})

db = firestore.client()

# db.collection("foods").add(
#     {"img_url": "", 
#      "is_processed":False})


@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/callback')
def authorized():

    if 'code' not in request.args:
        return 'Authorization request denied or invalid request', 400
    
    token = google.authorize_access_token()
    if not token:
        return 'Access denied or canceled by user', 400
    
    session['google_token'] = (token['access_token'], '')
    userinfo = google.get('userinfo')
    user_data = userinfo.json()

    users_ref = db.collection('users')
    user_ref = users_ref.document(user_data['id'])

    # Check if user exists in our db
    user_snapshot = user_ref.get()
    if user_snapshot.exists:
        # update existing user
        user_ref.update({
            'last_login': firestore.SERVER_TIMESTAMP
        })
    else:
        # create new user
        user_ref.set({
            'id': user_data['id'],
            'name': user_data['name'],
            'email': user_data['email'],
            'profile_picture': user_data['picture'],
            'created_at': firestore.SERVER_TIMESTAMP
        })

    session['user_id'] = user_data['id']
    return redirect(url_for('index'))


@app.route('/upload_image', methods=["POST"])
def upload_image():
    # if not session.get('is_admin'):
    #     return 'Access Denied', 403
    
    # # Check if the post request has the file part
    # if 'image' not in request.files:
    #     return 'No file part', 400
    
    image = request.files['image']
    
    # if image.filename == '':
    #     return 'No selected file', 400
    
    filename = secure_filename(image.filename)

    # Upload to Firebase Storage
    bucket = storage.bucket()

    blob = bucket.blob(filename)
    blob.upload_from_file(image)
    blob.make_public()
    image_url = blob.public_url

    food_data = {
        'img_url': image_url,
        'is_processed': False,
        'uploaded_at': firestore.SERVER_TIMESTAMP
    }

    db.collection('foods').add(food_data)

    return 'Image Uploaded Successfully', 200


@app.route('/upload_form')
def upload_form():
    return render_template("upload_form.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
                  debug=True)
