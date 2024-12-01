app.py
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
import mysql.connector
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email
from werkzeug.utils import secure_filename
import os, json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'please_amongbus'

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if the uploaded file is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='ecommerce'
    )
    return conn

def get_product_by_id(product_id):
    """Fetch a product from the database by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return product

@app.template_filter('number_format')
def number_format(value, decimal_places=2):
    """Format a number with a specific number of decimal places."""
    if value is None:
        return ''
    return f"{value:,.{decimal_places}f}"


def save_image(image_file):
    """Save the uploaded image file to the server and return the filename."""
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        return filename
    return None 

def update_product_in_db(product):
    """Update the product in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE products 
        SET name = %s, description = %s, price = %s, stock = %s, category = %s, color = %s,
            discount_value = %s, discount_type = %s, coupon_code = %s, image = %s
        WHERE id = %s
    ''', (product['name'], product['description'], product['price'], product['stock'],
          product['category'], product['color'], product['discount_value'], 
          product['discount_type'], product['coupon_code'], product['image'], product['id']))
    
    conn.commit()
    cursor.close()
    conn.close()

class StartSellingForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    shop_name = StringField('Shop Name', validators=[DataRequired()])
    shop_description = TextAreaField('Shop Description', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    region = StringField('Region/Province', validators=[DataRequired()])
    province = StringField('Province', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    barangay = StringField('Barangay', validators=[DataRequired()])
    postal_code = StringField('Postal Code', validators=[DataRequired()])
    submit = SubmitField('Start Selling')

    
@app.route('/', methods=['GET'])
def index():
    user_logged_in = 'username' in session  # Check if user is logged in
    user_initial = session['username'][0].upper() if user_logged_in else 'U'

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM products WHERE seller_id IS NOT NULL')
    seller_products = cursor.fetchall()

    cursor.execute('SELECT * FROM products WHERE flash_sale = TRUE')
    flash_sale_products = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('index.html', user_logged_in=user_logged_in, user_initial=user_initial, seller_products=seller_products, flash_sale_products=flash_sale_products)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Handle settings update logic here
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))  # Redirect to the same page after update
    return render_template('settings.html')  # Render the settings template

@app.route('/admin', methods=["GET"])
def admin():
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM seller_applications ORDER BY created_at DESC')
        applications = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('admin_panel.html', show_register=True, applications=applications)
    else:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))

@app.route('/superadmin', methods=["GET"])
def superadmin():
    if 'role' in session and session['role'] == 'superadmin':
        return render_template('superadmin.html', show_register=True)
    else:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))

@app.route('/register', methods=['GET'])
def show_register():
    return render_template('register.html', show_register=True)

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password'] 

    print(f"Attempting to register user: {username}, {email}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
        conn.commit()
        flash('Registration successful! You can now log in.', 'success')
        print("Registration successful")
        return redirect(url_for('login'))
    except mysql.connector.IntegrityError as e:
        conn.rollback()
        flash('Email already exists. Try a different one.', 'error')
        print(f"IntegrityError: {str(e)}")
        return render_template('register.html', username=username, email=email, show_register=True)
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
        print(f"Exception: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    return render_template('register.html', username=username, email =email, show_register=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        connection.close()
        
        if user:
            if user['password'] == password:
                session.permanent = True
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['username'] = user['username']
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin'))
                elif user['role'] == 'superadmin':
                    return redirect(url_for('superadmin'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid username or password')
                return redirect(url_for('login'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/redirectlogin', methods=['GET'])
def redirectlogin():
    return render_template('register.html')

@app.route('/start_selling', methods=['GET', 'POST'])
def start_selling():
    form = StartSellingForm()
    if form.validate_on_submit():
        full_name = form.full_name.data
        email = form.email.data
        shop_name = form.shop_name.data
        shop_description = form.shop_description.data
        phone_number = form.phone_number.data
        region = form.region.data
        province = form.province.data
        city = form.city.data
        barangay = form.barangay.data
        postal_code = form.postal_code.data

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM seller_applications WHERE email = %s', (email,))
            existing_application = cursor.fetchone()

            if existing_application:
                flash(f'An application with this email ({email}) already exists.', 'error')
                return render_template('start_selling.html', form=form)

            cursor.execute('INSERT INTO seller_applications (full_name, email, shop_name, shop_description, phone_number, region, province, city, barangay, postal_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                           (full_name, email, shop_name, shop_description, phone_number, region, province, city, barangay, postal_code))
            conn.commit()
            flash('Your application to start selling has been submitted!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred while submitting your application: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('start_selling.html', form=form)

@app.route('/seller_dashboard', methods=['GET'])
def seller_dashboard():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    page = request.args.get('page', 1, type=int)
    limit = 15
    offset = (page - 1) * limit

    cursor.execute('SELECT * FROM products WHERE seller_id = %s LIMIT %s OFFSET %s', (user_id, limit, offset))
    seller_products = cursor.fetchall()

    cursor.execute('SELECT * FROM products WHERE seller_id = %s', (user_id,))
    seller_products = cursor.fetchall()

    cursor.execute('SELECT COUNT(*) as total FROM products WHERE seller_id = %s', (user_id,))
    total_products = cursor.fetchone()['total']
    total_pages = (total_products + limit - 1) // limit 

    cursor.execute('SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC', (user_id,))
    notifications = cursor.fetchall()

    cursor.execute('''
        SELECT o.id, o.quantity, o.total_price, o.order_status, o.created_at, p.name, o.user_full_name, o.user_email 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE p.seller_id = %s
    ''', (user_id,))
    orders = cursor.fetchall()

    total_sales = sum(order['quantity'] for order in orders)
    total_revenue = sum(order['total_price'] for order in orders)

    cursor.execute('''
        SELECT o.id, o.total_price, o.created_at 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE p.seller_id = %s
        ORDER BY o.created_at DESC
        LIMIT 5
    ''', (user_id,))
    recent_orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('seller_dashboard.html', notifications=notifications, seller_products=seller_products, orders=orders, total_sales=total_sales, total_revenue=total_revenue, recent_orders=recent_orders, page=page, total_pages=total_pages)

@app.route('/add_product', methods=['POST'])
def add_product():
    product_name = request.form['product_name']
    product_description = request.form['product_description']
    product_price = request.form['product_price']
    product_stock = request.form['product_stock'] 
    product_category = request.form['product_category']
    product_color = request.form['product_color']
    product_image = request.files['product_image']

    discount_type = request.form.get('discount_type') 
    discount_value = request.form.get('product_discount', type=float)
    coupon_code = request.form.get('coupon_code') 
    
    flash_sale = request.form.get('flash_sale') == 'on' 

    if product_image and allowed_file(product_image.filename):
        filename = secure_filename(product_image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        product_image.save(image_path)

        additional_images = request.files.getlist('additional_images')
        additional_image_paths = []

        for img in additional_images:
            if img and allowed_file(img.filename):
                additional_filename = secure_filename(img.filename)
                additional_image_path = os.path.join(app.config['UPLOAD_FOLDER'], additional_filename)
                img.save(additional_image_path)
                additional_image_paths.append(additional_filename)
                additional_images_json = json.dumps(additional_image_paths)

                user_id = session.get('user_id')
                conn = get_db_connection()
                cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO products (name, description, price, stock, image, category, seller_id, color, discount_type, discount_value, coupon_code, flash_sale, additional_images) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (product_name, product_description, product_price, product_stock, filename, product_category, user_id, product_color, discount_type, discount_value, coupon_code, flash_sale, additional_images_json))
            conn.commit()
            flash('Product added successfully!', 'success')
        except mysql.connector.Error as e:
            conn.rollback()
            flash(f'An error occurred while adding the product: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Invalid image file. Please upload a valid image (png, jpg, jpeg, gif).', 'error')

    return redirect(url_for('seller_dashboard'))

@app.route('/admin/seller_applications', methods=['GET'])
def view_seller_applications():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM seller_applications ORDER BY created_at DESC')
    applications = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('view_seller_applications.html', applications=applications)

@app.route('/admin/update_application/<int:application_id>', methods=['POST'])
def update_application(application_id):
    status = request.form['status']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('SELECT * FROM seller_applications WHERE id = %s', (application_id,))
        application = cursor.fetchone()

        if application is None:
            flash('Application not found.', 'error')
            return redirect(url_for('admin'))

        if status == 'accepted':
            cursor.execute('UPDATE users SET role = %s WHERE email = %s', ('seller', application['email']))
            conn.commit()

            cursor.execute('INSERT INTO notifications (user_id, message) VALUES (%s, %s)', 
                           (application['user_id'], f'Your application has been accepted. Welcome to our seller community!'))
            conn.commit()

        cursor.execute('UPDATE seller_applications SET status = %s WHERE id = %s', (status, application_id))
        conn.commit()

        flash('Application status updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred while updating the application: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Handle form submission
        user_id = session.get('user_id')
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))
        total_price = float(request.form.get('total_price', 0.0))
        user_full_name = request.form.get('full_name')
        user_email = request.form.get('email')
        order_status = 'pending'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT seller_id FROM products WHERE id = %s', (product_id,))
        seller = cursor.fetchone()

        if seller:
            seller_id = seller['seller_id']

            cursor.execute(
                'INSERT INTO orders (user_id, product_id, quantity, total_price, user_full_name, user_email, order_status, seller_id) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (user_id, product_id, quantity, total_price, user_full_name, user_email, order_status, seller_id)
            )
            conn.commit() 
            cursor.close()
            conn.close()

            return redirect(url_for('index')) 
        else:
            cursor.close()
            conn.close()
            flash('Invalid product ID.', 'error')
            return redirect(url_for('index'))

    product_id = request.args.get('product_id')
    if product_id:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()

        if product:
            quantity = 1
            total_price = product['price'] * quantity

            return render_template('checkout.html', 
                                   product_id=product['id'], 
                                   product_name=product['name'], 
                                   quantity=quantity, 
                                   total_price=total_price)
        else:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))
    else:
        flash('No product selected for checkout.', 'error')
        return redirect(url_for('index'))
    
@app.route('/seller_dashboard/orders', methods=['GET'])
def seller_orders():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('''
        SELECT o.id, o.quantity, o.total_price, o.order_status, o.created_at, p.name, o.user_full_name, o.user_email 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE p.seller_id = %s
    ''', (user_id,))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('seller_dashboard.html', orders=orders)

from flask import redirect, url_for, session

@app.route('/logout', methods=['POST'])
def logout():
    session.clear() 
    return redirect(url_for('index'))

@app.route('/api/fetch_user_accounts/', methods=['GET'])
def fetch_user_accounts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, username, email, role FROM users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

DEFAULT_PRICE = 0.0
DEFAULT_QUANTITY = 0

@app.route('/cart', methods=['GET'])
def cart() -> str:
    cart_items: list[dict] = session.get('cart', [])
    
    for item in cart_items:
        price = float(item.get('price', DEFAULT_PRICE)) 
        quantity = int(item.get('quantity', DEFAULT_QUANTITY))
        if not isinstance(price, (int, float)) or not isinstance(quantity, int):
            price = DEFAULT_PRICE
            quantity = DEFAULT_QUANTITY
        item['subtotal'] = price * quantity

    return render_template('cart.html', cart_items=cart_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if product:
        if 'cart' not in session:
            session['cart'] = []


        price = float(product['price']) 

        for item in session['cart']:
            if item['id'] == product['id']:
                item['quantity'] += quantity
                item['subtotal'] = item['quantity'] * price
                break
        else:
            # If not in cart, add it
            session['cart'].append({
                'id': product['id'],
                'name': product['name'],
                'variation': data.get('variation'),
                'price': price,
                'quantity': quantity,
                'subtotal': price * quantity,
                'image': product['image']
            })

        session.modified = True
        return jsonify({'success': True, 'cart': session['cart']})
    
    return jsonify({'success': False, 'error': 'Product not found'}), 404

@app.route('/products', methods=['GET'])
def product_listing():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('product_detail.html', products=products)

@app.route('/product/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        
        if product:
            cursor.execute('''
                SELECT o.id, o.quantity, o.total_price, o.order_status, o.created_at 
                FROM orders o 
                WHERE o.product_id = %s
            ''', (product_id,))
            orders = cursor.fetchall()

            total_sales = sum(order['quantity'] for order in orders)
            total_revenue = sum(order['total_price'] for order in orders)

            recent_orders = orders[-5:] if orders else []

            return render_template('product_detail.html', product=product, orders=orders, total_sales=total_sales, total_revenue=total_revenue, recent_orders=recent_orders)
        else:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        flash('An error occurred while retrieving product details.', 'error')
        print(f"Error: {e}")
        return redirect(url_for('index'))
    
    finally:
        cursor.close()  
        conn.close()

@app.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    new_status = request.form['order_status']
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('UPDATE orders SET order_status = %s WHERE id = %s', (new_status, order_id))
        
        cursor.execute('SELECT user_id FROM orders WHERE id = %s', (order_id,))
        order = cursor.fetchone()

        if order:
            user_id = order['user_id']
            notification_message = f'Your order #{order_id} status has been updated to {new_status}.'
            cursor.execute('INSERT INTO notifications (user_id, message) VALUES (%s, %s)', (user_id, notification_message))
        
        conn.commit()
        flash('Order status updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred while updating the order status: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('seller_dashboard'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred while deleting the product: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('seller_dashboard'))


@app.route('/edit_order/<int:order_id>', methods=['POST'])
def edit_order(order_id):
    new_status = request.form.get('order_status') 
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('UPDATE orders SET order_status = %s WHERE id = %s', (new_status, order_id))
        conn.commit()
        flash('Order status updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred while updating the order status: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('seller_dashboard'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = get_product_by_id(product_id)
    if request.method == 'POST':
        product['name'] = request.form['product_name']
        product['description'] = request.form['product_description']
        product['price'] = float(request.form['product_price'])
        product['stock'] = int(request.form['product_stock'])
        product['color'] = request.form['product_color']
        product['discount_value'] = float(request.form['product_discount']) if request.form['product_discount'] else None
        product['discount_type'] = request.form['discount_type']
        product['coupon_code'] = request.form['product_coupon']

        if 'product_image' in request.files:
            file = request.files['product_image']
            new_image_filename = save_image(file)
            if new_image_filename:
                product['image'] = new_image_filename

        update_product_in_db(product) 
        flash('Product updated successfully!', 'success')
        return redirect(url_for('product_detail', product_id=product['id']))
    
    return render_template('edit_product.html', product=product)


if __name__ == '__main__':
    app.run(debug=True)