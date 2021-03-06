from flask import Flask, render_template, redirect, url_for, flash,abort,request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar
import smtplib
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('KEY')
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',"sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,size=100,rating='g',default='retro',force_default=False,force_lower=False,use_ssl=False,base_url=None)


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    author = relationship("User",back_populates="posts")
    comments = relationship("Comment",back_populates='post')


class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(250),nullable=False,unique=True)
    password = db.Column(db.String(250),nullable=False)
    name = db.Column(db.String(250),nullable=False)
    posts = relationship("BlogPost",back_populates="author")
    comments = relationship("Comment",back_populates='author')


class Comment(db.Model):

    __tablename__ = "comments"
    id = db.Column(db.Integer,primary_key=True)
    text = db.Column(db.String(1000),nullable=False)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('blog_posts.id'))
    post = relationship('BlogPost',back_populates="comments")
    author = relationship("User",back_populates="comments")







db.create_all()



def admin_only(f):

    
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if current_user.id != 1:
            abort(403)


        return f(*args,**kwargs)

    return decorated_function






@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=['GET','POST'])
def register():
    form= RegisterForm() 

    if form.validate_on_submit():

        email = form.email.data
        

        if User.query.filter_by(email=email).first():
            flash("You've already signed up with this email! Login instead!")
            return redirect(url_for('login'))

        name = form.name.data
        password= form.password.data
        hashed_password = generate_password_hash(password,method="pbkdf2:sha256",salt_length=8)

        user = User(email=email,name=name,password=hashed_password)
        db.session.add(user)
        db.session.commit()

        
        login_user(user)
        return redirect(url_for('get_all_posts'))



    return render_template("register.html",form=form)


@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()


        if user:
            if check_password_hash(user.password,password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Invalid Password!')
                return redirect(url_for('login'))
        else:
            flash('Email does not exist')
            return redirect(url_for('login'))


    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if form.validate_on_submit():

        if current_user.is_authenticated:
            body = form.body.data
            new_comment = Comment(text=body,author_id=current_user.id,post_id=post_id)
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post',post_id=post_id))
        else:
            flash("Please login to post comments!")
            return redirect(url_for('login'))

    return render_template("post.html", post=requested_post,form=form)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact",methods=['GET','POST'])
def contact():

    if request.method == 'POST':


        name = request.form['name']
        email = request.form['email']
        telephone = request.form['telephone']
        message = request.form['message']

        my_email= "calcguru2020@gmail.com"
        to_email = "ctabatab@gmail.com"

        message = f"Subject: Message From Blog!\n\n{name}\n{email}\n{telephone}\n{message}"
        with smtplib.SMTP('smtp.gmail.com',port=587) as connection:
            connection.starttls()
            connection.login(user=my_email,password=os.environ.get('PASSWORD'))
            connection.sendmail(from_addr=my_email,to_addrs=to_email,msg=message)



        flash("Message Sent!")




    return render_template("contact.html")

@app.route("/new-post",methods=['GET','POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=['GET','POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author.name,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
