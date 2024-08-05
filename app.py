from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_migrate import Migrate
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')  # Replace with a real secret key
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'wmv'}
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set up OpenAI API
MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "<your OpenAI API key if not set as an env var>"))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_url = db.Column(db.String(200), nullable=True)  # Optional field for featured image

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    blog = db.relationship('Blog', backref=db.backref('images', lazy=True))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/blog')
def blog():
    posts = Blog.query.order_by(Blog.date_posted.desc()).all()
    return render_template('blog.html', posts=posts)

@app.route('/blog/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash('Title and content are required!', 'danger')
            return redirect(url_for('new_post'))

        new_post = Blog(title=title, content=content)
        db.session.add(new_post)
        db.session.commit()

        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + "_" + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                image_url = url_for('static', filename='uploads/' + unique_filename)
                image = Image(blog_id=new_post.id, image_url=image_url)
                db.session.add(image)
                db.session.commit()

        flash('Your post has been created!', 'success')
        return redirect(url_for('blog'))
    return render_template('create_post.html')

@app.route('/blog/<int:post_id>')
def post(post_id):
    post = Blog.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + "_" + filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        return jsonify({'location': url_for('static', filename='uploads/' + unique_filename)})
    return jsonify({'error': 'File not allowed'}), 400

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/chatbot/ask', methods=['POST'])
def ask_chatbot():
    user_message = request.form['message']
    
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_response = completion.choices[0].message.content
    except Exception as e:
        bot_response = f"An error occurred: {str(e)}"
    
    return jsonify({'response': bot_response})

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        # Here you would typically send an email
        # For demonstration purposes, we'll just print the message
        print(f"New message from {name} ({email}): {message}")
        
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
