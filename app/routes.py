import os
import uuid
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, text
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import ActivityLog, CartItem, Category, OrderItem, Product, User

bp = Blueprint("main", __name__)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


# ---------- public pages ----------

@bp.get("/")
def home():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    query = Product.query.filter_by(active=True)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter_by(category_id=category_id)
    products = query.order_by(Product.id.desc()).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template(
        "home.html", products=products, categories=categories, q=q, category_id=category_id
    )


@bp.get("/product/<int:product_id>")
def product(product_id):
    p = db.session.get(Product, product_id)
    if not p or not p.active:
        abort(404)
    return render_template("product.html", p=p)


@bp.get("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.get("/health")
def health():
    db.session.execute(text("SELECT 1"))  # fails if the database is unreachable
    return {"status": "ok"}, 200


# ---------- accounts ----------

@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Fill in all fields. Password must be at least 8 characters.")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.")
        else:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("main.home"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("main.home"))
        flash("Wrong email or password.")
    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))


# ---------- admin: products ----------

def save_product(p):
    """Validate the form and save the product. Returns True on success."""
    name = request.form.get("name", "").strip()
    try:
        price = Decimal(request.form.get("price", ""))
        stock = int(request.form.get("stock", "0"))
        if not price.is_finite():
            raise ValueError
    except (InvalidOperation, ValueError):
        flash("Enter a valid price and stock.")
        return False
    if not name or price <= 0 or stock < 0:
        flash("Name is required, price must be above 0 and stock cannot be negative.")
        return False

    image = request.files.get("image")
    new_image_url = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in ALLOWED_EXT:
            flash("Image must be a jpg, png or webp file.")
            return False
        filename = f"{uuid.uuid4().hex}{ext}"
        image.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        new_image_url = url_for("main.uploads", filename=filename)

    p.name = name
    p.description = request.form.get("description", "").strip()
    p.category_id = request.form.get("category_id", type=int)
    p.price_paise = int((price * 100).to_integral_value())  # money as whole paise
    p.stock = stock
    p.active = request.form.get("active") == "on"
    if new_image_url:
        p.image_url = new_image_url
    db.session.add(p)
    db.session.commit()
    return True


@bp.get("/admin/products")
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin_products.html", products=products)


@bp.route("/admin/products/new", methods=["GET", "POST"])
@admin_required
def admin_product_new():
    if request.method == "POST" and save_product(Product()):
        flash("Product added.")
        return redirect(url_for("main.admin_products"))
    categories = Category.query.order_by(Category.name).all()
    return render_template("admin_product_form.html", p=None, categories=categories)


@bp.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_edit(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    if request.method == "POST" and save_product(p):
        flash("Product updated.")
        return redirect(url_for("main.admin_products"))
    categories = Category.query.order_by(Category.name).all()
    return render_template("admin_product_form.html", p=p, categories=categories)


# ---------- admin: categories ----------

@bp.route("/admin/categories", methods=["GET", "POST"])
@admin_required
def admin_categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name and not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
            db.session.commit()
            flash("Category added.")
        else:
            flash("Enter a category name that does not exist yet.")
        return redirect(url_for("main.admin_categories"))
    categories = Category.query.order_by(Category.name).all()
    return render_template("admin_categories.html", categories=categories)


@bp.post("/admin/products/<int:product_id>/delete")
@admin_required
def admin_product_delete(product_id):

    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    if OrderItem.query.filter_by(product_id=p.id).first():
        flash("This product is in past orders, so it can't be deleted. Hide it instead.")
        return redirect(url_for("main.admin_products"))

    image_url = p.image_url
    CartItem.query.filter_by(product_id=p.id).delete()
    ActivityLog.query.filter_by(product_id=p.id).delete()
    db.session.delete(p)
    db.session.commit()

    if image_url and image_url.startswith("/uploads/"):
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], image_url.rsplit("/", 1)[-1])
        if os.path.exists(path):
            os.remove(path)

    flash("Product deleted.")
    return redirect(url_for("main.admin_products"))


# ---------- cart ----------

@bp.app_context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        count = (
            db.session.query(func.coalesce(func.sum(CartItem.quantity), 0))
            .filter(CartItem.user_id == current_user.id)
            .scalar()
        )
        return {"cart_count": int(count)}
    return {"cart_count": 0}


def cart_rows(user):
    return (
        db.session.query(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .filter(CartItem.user_id == user.id)
        .order_by(CartItem.id)
        .all()
    )


@bp.get("/cart")
@login_required
def cart():
    rows = cart_rows(current_user)
    lines = [(item, p, item.quantity * p.price_paise) for item, p in rows]
    total = sum(line[2] for line in lines)  # calculated on the server
    return render_template("cart.html", lines=lines, total=total)


@bp.post("/cart/add/<int:product_id>")
@login_required
def cart_add(product_id):
    p = db.session.get(Product, product_id)
    if not p or not p.active:
        abort(404)
    if p.stock <= 0:
        flash("Sorry, that product is out of stock.")
        return redirect(url_for("main.product", product_id=p.id))

    qty = max(request.form.get("quantity", 1, type=int), 1)
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=p.id).first()
    wanted = qty + (item.quantity if item else 0)
    if wanted > p.stock:
        wanted = p.stock
        flash(f"Only {p.stock} available, so your cart has {p.stock}.")

    if item:
        item.quantity = wanted
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=p.id, quantity=wanted))
    db.session.commit()
    return redirect(url_for("main.cart"))


@bp.post("/cart/update/<int:item_id>")
@login_required
def cart_update(item_id):
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != current_user.id:
        abort(404)
    qty = request.form.get("quantity", type=int)
    if qty is None:
        abort(400)

    p = db.session.get(Product, item.product_id)
    if qty > p.stock:
        qty = p.stock
        flash(f"Only {p.stock} available.")
    if qty <= 0:
        db.session.delete(item)
    else:
        item.quantity = qty
    db.session.commit()
    return redirect(url_for("main.cart"))


@bp.post("/cart/remove/<int:item_id>")
@login_required
def cart_remove(item_id):
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != current_user.id:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("main.cart"))
