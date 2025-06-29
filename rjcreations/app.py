from flask import Flask, render_template, redirect, url_for, session, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_bcrypt import Bcrypt
from forms import RegisterForm, LoginForm
from models import db, User, Product
from config import Config
import razorpay

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

razorpay_client = razorpay.Client(auth=(app.config["RAZORPAY_KEY_ID"], app.config["RAZORPAY_KEY_SECRET"]))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()
    if not Product.query.first():
        p1 = Product(name="Custom Mug", price=15.99, image="mug.jpg", description="A personalized mug.")
        p2 = Product(name="Photo T-Shirt", price=20.00, image="shirt.jpg", description="T-shirt with custom print.")
        p3 = Product(name="Personalized Pillow", price=18.50, image="pillow.jpg", description="Soft pillow with photo.")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    flash("Added to cart")
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        subtotal = qty * product.price
        total += subtotal
        items.append({'product': product, 'qty': qty, 'subtotal': subtotal})

    if total > 0:
        razorpay_order = razorpay_client.order.create(dict(amount=int(total*100), currency='INR', payment_capture='1'))
    else:
        razorpay_order = None

    return render_template('cart.html', items=items, total=total, razorpay_order=razorpay_order)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(email=form.email.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registered successfully.")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid credentials.")
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/admin/delete/<int:id>')
@login_required
def delete_product(id):
    if not current_user.is_admin:
        abort(403)
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
