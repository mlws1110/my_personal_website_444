from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_migrate import Migrate
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI
import stripe

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

# Add Stripe API key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

CASHAPP_HANDLE = '$YourCashAppHandle'  # Replace with your actual Cash App handle

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_url = db.Column(db.String(200), nullable=True)  # Optional field for featured image
    category = db.Column(db.String(50), nullable=True)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    blog = db.relationship('Blog', backref=db.backref('images', lazy=True))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/blog')
@app.route('/blog/<category>')
def blog(category=None):
    # You can filter blog posts by category if provided
    if category:
        # Logic to fetch blog posts for the specific category
        posts = get_posts_by_category(category)
    else:
        # Logic to fetch all blog posts
        posts = get_all_posts()
    return render_template('blog.html', posts=posts, category=category)

@app.route('/tools')
def tools():
    # Logic to fetch tools and resources
    tools_list = get_tools_list()
    return render_template('tools.html', tools=tools_list)

@app.route('/projects')
def projects():
    # Logic to fetch your projects
    projects_list = get_projects_list()
    return render_template('projects.html', projects=projects_list)

@app.route('/blog/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')

        if not title or not content or not category:
            flash('Title, content, and category are required!', 'danger')
            return redirect(url_for('new_post'))

        new_post = Blog(title=title, content=content, category=category)
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

CASHAPP_HANDLE = '$Green1110'  # Your actual Cash App handle

@app.route('/tip-jar')
def tip_jar():
    return render_template('tip_jar.html', cashapp_handle=CASHAPP_HANDLE)

# Helper functions (you'll need to implement these)
def get_posts_by_category(category):
    return Blog.query.filter_by(category=category).order_by(Blog.date_posted.desc()).all()

def get_all_posts():
    return Blog.query.order_by(Blog.date_posted.desc()).all()

def get_tools_list():
    return [
        {
            "name": "ChatGPT",
            "description": "OpenAI's powerful language model for conversation and text generation.",
            "link": "https://chat.openai.com/"
        },
        {
            "name": "GPT-4",
            "description": "OpenAI's most advanced language model, capable of understanding and generating human-like text.",
            "link": "https://openai.com/gpt-4"
        },
        {
            "name": "Claude",
            "description": "Anthropic's AI assistant, known for its strong reasoning capabilities.",
            "link": "https://www.anthropic.com/"
        },
        {
            "name": "DALL-E 2",
            "description": "OpenAI's AI system that can create realistic images and art from natural language descriptions.",
            "link": "https://openai.com/dall-e-2"
        },
        {
            "name": "Midjourney",
            "description": "An AI-powered tool that generates images from textual descriptions.",
            "link": "https://www.midjourney.com/"
        },
        {
            "name": "Stable Diffusion",
            "description": "An open-source image generation model capable of producing detailed images from text descriptions.",
            "link": "https://stablediffusionweb.com/"
        },
        {
            "name": "Google Bard",
            "description": "Google's conversational AI powered by LaMDA.",
            "link": "https://bard.google.com/"
        },
        {
            "name": "Hugging Face",
            "description": "A platform offering a wide range of open-source machine learning models and datasets.",
            "link": "https://huggingface.co/"
        },
        {
            "name": "Replicate",
            "description": "A platform for running machine learning models in the cloud, including various image generation models.",
            "link": "https://replicate.com/"
        },
        {
            "name": "RunwayML",
            "description": "A creative toolkit powered by machine learning, offering various AI-powered creative tools.",
            "link": "https://runwayml.com/"
        },
        {
            "name": "LangChain",
            "description": "A framework for developing applications powered by language models.",
            "link": "https://langchain.com/"
        },
        {
            "name": "Cohere",
            "description": "A platform offering powerful language AI models through simple APIs.",
            "link": "https://cohere.ai/"
        }
    ]

def get_projects_list():
    # This is a placeholder. In a real application, you'd fetch this from a database.
    return [
        {"name": "Personal Blog", "description": "A Flask-based blog application", "link": "/blog"},
        {"name": "AI Chatbot", "description": "An AI-powered chatbot using OpenAI's GPT", "link": "/chatbot"},
        {"name": "Fintech Analysis Tool", "description": "A tool for analyzing financial data", "link": "#"},
    ]

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
