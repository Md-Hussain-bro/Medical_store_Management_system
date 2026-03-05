"""
Medical Store Management System
Main Application File - Multi-Tenant Architecture
"""
import sys
import os
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, session
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from models import db, User, Store, Medicine, Sale, SaleItem


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Initialize Flask application
app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
    instance_path=resource_path("instance")
)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key'
os.makedirs(app.instance_path, exist_ok=True)

db_path = os.path.join(app.instance_path, "pharmacy.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'


# ── FIX 2: Use db.session.get() instead of deprecated Query.get() ──
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ==================== HELPER / DECORATORS ====================

def get_store_id():
    """Get current user's store_id. Returns None for superadmin."""
    if current_user.is_authenticated:
        return current_user.store_id
    return None


def store_required(f):
    """Decorator: user must belong to a store."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.store_id is None:
            flash('You need to be associated with a store to access this page.', 'warning')
            return redirect(url_for('admin_dashboard'))
        if not current_user.store.is_active:
            flash('Your store account has been deactivated. Contact administrator.', 'danger')
            logout_user()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def superadmin_required(f):
    """Decorator: only superadmin can access."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_superadmin:
            flash('Access denied. Superadmin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def owner_required(f):
    """Decorator: only store owner (or superadmin) can access."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not (current_user.is_superadmin or current_user.is_owner):
            flash('Access denied. Store owner privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def init_db():
    """Initialize database and create default superadmin"""
    db.create_all()

    # Create default superadmin (no store)
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            full_name='System Administrator',
            role='superadmin',
            store_id=None
        )
        admin.set_password('admin123')
        db.session.add(admin)

    # Create a demo store with owner for testing
    if not Store.query.filter_by(name='Demo Pharmacy').first():
        demo_store = Store(
            name='Demo Pharmacy',
            address='123 Demo Street',
            phone='1234567890',
            email='demo@pharmacy.com'
        )
        db.session.add(demo_store)
        db.session.flush()

        if not User.query.filter_by(username='demo_owner').first():
            owner = User(
                username='demo_owner',
                full_name='Demo Store Owner',
                role='owner',
                store_id=demo_store.id
            )
            owner.set_password('owner123')
            db.session.add(owner)

        if not User.query.filter_by(username='demo_staff').first():
            staff = User(
                username='demo_staff',
                full_name='Demo Staff',
                role='staff',
                store_id=demo_store.id
            )
            staff.set_password('staff123')
            db.session.add(staff)

    db.session.commit()
    print("Database initialized successfully!")


with app.app_context():
    init_db()


# Context processor
@app.context_processor
def inject_globals():
    return {
        'now': datetime.now(),
        'today': date.today(),
        'get_store_id': get_store_id
    }


# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_superadmin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_superadmin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact administrator.', 'danger')
                return render_template('login.html')

            # Check store is active (skip for superadmin)
            if user.store_id and not user.store.is_active:
                flash('Your store account has been deactivated. Contact administrator.', 'danger')
                return render_template('login.html')

            login_user(user)
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')

            if user.is_superadmin:
                return redirect(url_for('admin_dashboard'))

            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ==================== SUPERADMIN ROUTES ====================

@app.route('/admin')
@superadmin_required
def admin_dashboard():
    """Superadmin dashboard - overview of all stores"""
    stores = Store.query.order_by(Store.created_at.desc()).all()
    total_stores = Store.query.filter(Store.is_active.is_(True)).count()
    total_users = User.query.filter(User.role != 'superadmin').count()

    total_medicines = Medicine.query.filter(Medicine.is_active.is_(True)).count()
    today = date.today()
    today_sales = Sale.query.filter(
        db.func.date(Sale.sale_date) == today
    ).all()
    today_revenue = sum(s.total_amount for s in today_sales)

    return render_template('admin/dashboard.html',
        stores=stores,
        total_stores=total_stores,
        total_users=total_users,
        total_medicines=total_medicines,
        today_revenue=today_revenue,
        today_sales_count=len(today_sales)
    )


@app.route('/admin/stores')
@superadmin_required
def admin_stores():
    """List all stores"""
    stores = Store.query.order_by(Store.name).all()
    return render_template('admin/stores.html', stores=stores)


@app.route('/admin/stores/add', methods=['GET', 'POST'])
@superadmin_required
def admin_add_store():
    """Create a new store with its owner account"""
    if request.method == 'POST':
        try:
            store_name = request.form.get('store_name', '').strip()
            address = request.form.get('address', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            license_no = request.form.get('license_no', '').strip()

            owner_username = request.form.get('owner_username', '').strip()
            owner_password = request.form.get('owner_password', '').strip()
            owner_fullname = request.form.get('owner_fullname', '').strip()

            if not store_name or not owner_username or not owner_password:
                flash('Store name, owner username and password are required.', 'danger')
                return render_template('admin/add_store.html')

            if len(owner_password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('admin/add_store.html')

            if User.query.filter_by(username=owner_username).first():
                flash(f'Username "{owner_username}" already exists.', 'danger')
                return render_template('admin/add_store.html')

            store = Store(
                name=store_name,
                address=address,
                phone=phone,
                email=email,
                license_no=license_no
            )
            db.session.add(store)
            db.session.flush()

            owner = User(
                username=owner_username,
                full_name=owner_fullname,
                role='owner',
                store_id=store.id
            )
            owner.set_password(owner_password)
            db.session.add(owner)

            db.session.commit()
            flash(f'Store "{store_name}" created with owner "{owner_username}".', 'success')
            return redirect(url_for('admin_stores'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating store: {str(e)}', 'danger')

    return render_template('admin/add_store.html')


@app.route('/admin/stores/<int:store_id>/toggle', methods=['POST'])
@superadmin_required
def admin_toggle_store(store_id):
    """Activate/deactivate a store"""
    store = db.session.get(Store, store_id)
    if not store:
        flash('Store not found.', 'danger')
        return redirect(url_for('admin_stores'))

    store.is_active = not store.is_active
    db.session.commit()
    status = 'activated' if store.is_active else 'deactivated'
    flash(f'Store "{store.name}" has been {status}.', 'success')
    return redirect(url_for('admin_stores'))


@app.route('/admin/stores/<int:store_id>/users')
@superadmin_required
def admin_store_users(store_id):
    """View users of a specific store"""
    store = db.session.get(Store, store_id)
    if not store:
        flash('Store not found.', 'danger')
        return redirect(url_for('admin_stores'))

    users = User.query.filter_by(store_id=store_id).order_by(User.username).all()
    return render_template('admin/store_users.html', store=store, users=users)


# ==================== STORE USER MANAGEMENT (Owner) ====================

@app.route('/manage-users')
@store_required
@owner_required
def manage_users():
    """Store owner can manage staff users"""
    sid = current_user.store_id
    users = User.query.filter_by(store_id=sid).order_by(User.username).all()
    return render_template('manage_users.html', users=users)


@app.route('/manage-users/add', methods=['GET', 'POST'])
@store_required
@owner_required
def add_user():
    """Store owner adds a staff user"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            full_name = request.form.get('full_name', '').strip()
            role = request.form.get('role', 'staff').strip()

            if role not in ('staff', 'owner'):
                role = 'staff'

            if not username or not password:
                flash('Username and password are required.', 'danger')
                return render_template('add_user.html')

            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('add_user.html')

            if User.query.filter_by(username=username).first():
                flash(f'Username "{username}" already exists.', 'danger')
                return render_template('add_user.html')

            user = User(
                username=username,
                full_name=full_name,
                role=role,
                store_id=current_user.store_id
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            flash(f'User "{username}" created successfully.', 'success')
            return redirect(url_for('manage_users'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')

    return render_template('add_user.html')


@app.route('/manage-users/<int:user_id>/toggle', methods=['POST'])
@store_required
@owner_required
def toggle_user(user_id):
    """Activate/deactivate a staff user"""
    # ── FIX 1 & 4: Store-safe lookup ──
    user = User.query.filter_by(
        id=user_id,
        store_id=current_user.store_id
    ).first_or_404()

    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('manage_users'))

    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User "{user.username}" has been {status}.', 'success')
    return redirect(url_for('manage_users'))


@app.route('/manage-users/<int:user_id>/reset-password', methods=['POST'])
@store_required
@owner_required
def reset_user_password(user_id):
    """Reset a staff user's password"""
    # ── FIX 1 & 4: Store-safe lookup ──
    user = User.query.filter_by(
        id=user_id,
        store_id=current_user.store_id
    ).first_or_404()

    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('manage_users'))

    user.set_password(new_password)
    db.session.commit()
    flash(f'Password reset for "{user.username}".', 'success')
    return redirect(url_for('manage_users'))


# ==================== STORE DASHBOARD ====================

@app.route('/dashboard')
@store_required
def dashboard():
    """Display store dashboard - filtered by store_id"""
    sid = current_user.store_id

    # ── FIX 3: .is_(True) instead of == True ──
    total_medicines = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid
    ).count()

    low_stock_medicines = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid,
        Medicine.quantity < 10
    ).all()
    low_stock_count = len(low_stock_medicines)

    expiry_date_threshold = date.today() + timedelta(days=30)
    expiring_medicines = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid,
        Medicine.expiry_date <= expiry_date_threshold,
        Medicine.expiry_date >= date.today()
    ).all()
    expiring_count = len(expiring_medicines)

    today = date.today()
    today_sales = Sale.query.filter(
        Sale.store_id == sid,
        db.func.date(Sale.sale_date) == today
    ).all()
    today_revenue = sum(sale.total_amount for sale in today_sales)
    today_sales_count = len(today_sales)

    medicines = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid
    ).all()
    total_stock_value = sum(m.quantity * m.purchase_price for m in medicines)

    recent_sales = Sale.query.filter(
        Sale.store_id == sid
    ).order_by(Sale.sale_date.desc()).limit(5).all()

    return render_template('dashboard.html',
        total_medicines=total_medicines,
        low_stock_count=low_stock_count,
        low_stock_medicines=low_stock_medicines,
        expiring_count=expiring_count,
        expiring_medicines=expiring_medicines,
        today_revenue=today_revenue,
        today_sales_count=today_sales_count,
        total_stock_value=total_stock_value,
        recent_sales=recent_sales
    )


# ==================== INVENTORY ROUTES ====================

@app.route('/inventory')
@store_required
def inventory():
    """Display medicines - filtered by store_id"""
    sid = current_user.store_id
    search = request.args.get('search', '').strip()

    # ── FIX 3: .is_(True) ──
    query = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid
    )

    if search:
        query = query.filter(
            db.or_(
                Medicine.name.ilike(f'%{search}%'),
                Medicine.generic_name.ilike(f'%{search}%'),
                Medicine.batch_no.ilike(f'%{search}%')
            )
        )

    medicines = query.order_by(Medicine.name).all()
    return render_template('inventory.html', medicines=medicines, search=search)


@app.route('/inventory/add', methods=['GET', 'POST'])
@store_required
def add_medicine():
    """Add new medicine - auto-assign store_id"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            generic_name = request.form.get('generic_name', '').strip()
            batch_no = request.form.get('batch_no', '').strip()
            expiry_date = request.form.get('expiry_date')
            quantity = int(request.form.get('quantity', 0))
            purchase_price = float(request.form.get('purchase_price', 0))
            selling_price = float(request.form.get('selling_price', 0))
            supplier = request.form.get('supplier', '').strip()

            if not name or not batch_no or not expiry_date:
                flash('Please fill in all required fields.', 'danger')
                return render_template('add_medicine.html')

            if quantity < 0:
                flash('Quantity cannot be negative.', 'danger')
                return render_template('add_medicine.html')

            if purchase_price < 0 or selling_price < 0:
                flash('Prices cannot be negative.', 'danger')
                return render_template('add_medicine.html')

            medicine_type = request.form.get('medicine_type', 'tablet').strip()
            units_per_pack = request.form.get('units_per_pack', '').strip()
            units_per_pack = int(units_per_pack) if units_per_pack else None

            medicine = Medicine(
                store_id=current_user.store_id,
                name=name,
                generic_name=generic_name,
                medicine_type=medicine_type,
                units_per_pack=units_per_pack,
                batch_no=batch_no,
                expiry_date=datetime.strptime(expiry_date, '%Y-%m-%d').date(),
                quantity=quantity,
                purchase_price=purchase_price,
                selling_price=selling_price,
                supplier=supplier
            )

            db.session.add(medicine)
            db.session.commit()

            flash(f'Medicine "{name}" added successfully!', 'success')
            return redirect(url_for('inventory'))

        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medicine: {str(e)}', 'danger')

    return render_template('add_medicine.html')


@app.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@store_required
def edit_medicine(id):
    """Edit medicine - store-safe lookup"""
    # ── FIX 4: Single query with store_id, no separate manual check ──
    medicine = Medicine.query.filter_by(
        id=id,
        store_id=current_user.store_id
    ).first_or_404()

    if request.method == 'POST':
        try:
            medicine.name = request.form.get('name', '').strip()
            medicine.generic_name = request.form.get('generic_name', '').strip()
            medicine.batch_no = request.form.get('batch_no', '').strip()
            medicine.expiry_date = datetime.strptime(
                request.form.get('expiry_date'), '%Y-%m-%d'
            ).date()
            medicine.quantity = int(request.form.get('quantity', 0))
            medicine.purchase_price = float(request.form.get('purchase_price', 0))
            medicine.selling_price = float(request.form.get('selling_price', 0))
            medicine.supplier = request.form.get('supplier', '').strip()

            medicine_type = request.form.get('medicine_type', medicine.medicine_type).strip()
            medicine.medicine_type = medicine_type
            units_per_pack = request.form.get('units_per_pack', '').strip()
            medicine.units_per_pack = int(units_per_pack) if units_per_pack else None

            if not medicine.name or not medicine.batch_no:
                flash('Please fill in all required fields.', 'danger')
                return render_template('edit_medicine.html', medicine=medicine)

            db.session.commit()
            flash(f'Medicine "{medicine.name}" updated successfully!', 'success')
            return redirect(url_for('inventory'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating medicine: {str(e)}', 'danger')

    return render_template('edit_medicine.html', medicine=medicine)


@app.route('/inventory/delete/<int:id>', methods=['POST'])
@store_required
def delete_medicine(id):
    """Soft delete medicine - store-safe lookup"""
    # ── FIX 4: Single query with store_id ──
    medicine = Medicine.query.filter_by(
        id=id,
        store_id=current_user.store_id
    ).first_or_404()

    try:
        name = medicine.name
        medicine.is_active = False
        db.session.commit()
        flash(f'Medicine "{name}" removed from inventory successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing medicine: {str(e)}', 'danger')

    return redirect(url_for('inventory'))


# ==================== SALES ROUTES ====================

@app.route('/sales')
@store_required
def sales():
    return render_template('sales.html')


@app.route('/api/search-medicine')
@store_required
def search_medicine():
    """Search medicines - filtered by store_id, returns type info for unit selling"""
    sid = current_user.store_id
    query = request.args.get('q', '').strip()

    if len(query) < 1:
        return jsonify([])

    medicines = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid,
        Medicine.quantity > 0,
        Medicine.expiry_date >= date.today(),
        db.or_(
            Medicine.name.ilike(f'%{query}%'),
            Medicine.batch_no.ilike(f'%{query}%')
        )
    ).limit(10).all()

    return jsonify([{
        'id': m.id,
        'name': m.name,
        'generic_name': m.generic_name,
        'batch_no': m.batch_no,
        'quantity': m.quantity,
        'selling_price': m.selling_price,
        'expiry_date': m.expiry_date.strftime('%Y-%m-%d'),
        'medicine_type': m.medicine_type,
        'units_per_pack': m.units_per_pack
    } for m in medicines])


@app.route('/api/process-sale', methods=['POST'])
@store_required
def process_sale():
    """Process a sale - supports unit-level selling for tablets/capsules"""
    try:
        sid = current_user.store_id
        data = request.get_json()
        cart_items = data.get('items', [])
        customer_name = data.get('customer_name', '').strip()

        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})

        # ── Validation pass ──
        for item in cart_items:
            medicine = Medicine.query.filter_by(
                id=item['medicine_id'],
                store_id=sid
            ).first()
            if not medicine:
                return jsonify({
                    'success': False,
                    'message': 'Invalid medicine selection'
                })

            # Determine how many individual units are being sold
            units_sold = item.get('units', 0) or 0
            packs_sold = item.get('quantity', 0) or 0

            if medicine.is_countable and units_sold > 0:
                # Selling individual tablets/capsules
                # Stock is stored as total individual units for countable items
                if units_sold < 1:
                    return jsonify({
                        'success': False,
                        'message': f'At least 1 unit required for {medicine.name}'
                    })
                if units_sold > medicine.quantity:
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient stock for {medicine.name}. '
                                   f'Available: {medicine.quantity} units'
                    })
            else:
                # Selling by packs (non-countable or no units specified)
                if packs_sold < 1:
                    return jsonify({
                        'success': False,
                        'message': f'At least 1 pack required for {medicine.name}'
                    })
                if packs_sold > medicine.quantity:
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient stock for {medicine.name}. '
                                   f'Available: {medicine.quantity} packs'
                    })

        # ── Create sale ──
        invoice_no = Sale.generate_invoice_no(sid)
        total_amount = sum(item['subtotal'] for item in cart_items)

        sale = Sale(
            store_id=sid,
            invoice_no=invoice_no,
            customer_name=customer_name if customer_name else None,
            total_amount=total_amount,
            created_by=current_user.id
        )
        db.session.add(sale)
        db.session.flush()

        # ── Create sale items and deduct stock ──
        for item in cart_items:
            medicine = Medicine.query.filter_by(
                id=item['medicine_id'],
                store_id=sid
            ).first()

            units_sold = item.get('units', 0) or 0
            packs_sold = item.get('quantity', 0) or 0

            # Determine the quantity to record and stock to deduct
            if medicine.is_countable and units_sold > 0:
                record_quantity = units_sold
                stock_deduction = units_sold
            else:
                record_quantity = packs_sold
                stock_deduction = packs_sold

            sale_item = SaleItem(
                sale_id=sale.id,
                store_id=sid,
                medicine_id=item['medicine_id'],
                quantity=record_quantity,
                unit_price=item['unit_price'],
                subtotal=item['subtotal']
            )
            db.session.add(sale_item)
            medicine.quantity -= stock_deduction

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Sale processed successfully',
            'invoice_no': invoice_no,
            'sale_id': sale.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/bill/<int:sale_id>')
@store_required
def view_bill(sale_id):
    """View bill - store-safe lookup"""
    # ── FIX 4: Single query with store_id ──
    sale = Sale.query.filter_by(
        id=sale_id,
        store_id=current_user.store_id
    ).first_or_404()

    return render_template('bill.html', sale=sale)


# ==================== REPORTS ROUTES ====================

@app.route('/reports')
@store_required
def reports():
    return render_template('reports.html')


@app.route('/reports/daily')
@store_required
def daily_report():
    """Daily sales report - filtered by store_id"""
    sid = current_user.store_id
    report_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))

    try:
        selected_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except:
        selected_date = date.today()

    sales_list = Sale.query.filter(
        Sale.store_id == sid,
        db.func.date(Sale.sale_date) == selected_date
    ).order_by(Sale.sale_date.desc()).all()

    total_revenue = sum(sale.total_amount for sale in sales_list)
    total_items = sum(len(sale.items) for sale in sales_list)

    return render_template('daily_report.html',
        sales=sales_list,
        selected_date=selected_date,
        total_revenue=total_revenue,
        total_sales=len(sales_list),
        total_items=total_items
    )


@app.route('/reports/date-range')
@store_required
def date_range_report():
    """Date range report - filtered by store_id"""
    sid = current_user.store_id
    from_date = request.args.get(
        'from_date',
        (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    )
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))

    try:
        start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    except:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

    sales_list = Sale.query.filter(
        Sale.store_id == sid,
        db.func.date(Sale.sale_date) >= start_date,
        db.func.date(Sale.sale_date) <= end_date
    ).order_by(Sale.sale_date.desc()).all()

    total_revenue = sum(sale.total_amount for sale in sales_list)

    daily_data = {}
    for sale in sales_list:
        day = sale.sale_date.strftime('%Y-%m-%d')
        if day not in daily_data:
            daily_data[day] = {'count': 0, 'revenue': 0}
        daily_data[day]['count'] += 1
        daily_data[day]['revenue'] += sale.total_amount

    return render_template('date_range_report.html',
        sales=sales_list,
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_revenue,
        total_sales=len(sales_list),
        daily_data=daily_data
    )


@app.route('/reports/stock')
@store_required
def stock_report():
    """Stock report - filtered by store_id"""
    sid = current_user.store_id

    # ── FIX 3: .is_(True) ──
    medicines = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid
    ).order_by(Medicine.name).all()

    total_stock_value = sum(m.quantity * m.purchase_price for m in medicines)
    total_retail_value = sum(m.quantity * m.selling_price for m in medicines)
    potential_profit = total_retail_value - total_stock_value

    low_stock = [m for m in medicines if m.quantity < 10]
    out_of_stock = [m for m in medicines if m.quantity == 0]

    return render_template('stock_report.html',
        medicines=medicines,
        total_stock_value=total_stock_value,
        total_retail_value=total_retail_value,
        potential_profit=potential_profit,
        low_stock_count=len(low_stock),
        out_of_stock_count=len(out_of_stock)
    )


@app.route('/reports/expiry')
@store_required
def expiry_report():
    """Expiry report - filtered by store_id"""
    sid = current_user.store_id
    today = date.today()
    threshold = today + timedelta(days=30)

    # ── FIX 3: .is_(True) ──
    expired = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid,
        Medicine.expiry_date < today,
        Medicine.quantity > 0
    ).order_by(Medicine.expiry_date).all()

    expiring_soon = Medicine.query.filter(
        Medicine.is_active.is_(True),
        Medicine.store_id == sid,
        Medicine.expiry_date >= today,
        Medicine.expiry_date <= threshold,
        Medicine.quantity > 0
    ).order_by(Medicine.expiry_date).all()

    expired_value = sum(m.quantity * m.purchase_price for m in expired)
    expiring_value = sum(m.quantity * m.purchase_price for m in expiring_soon)

    return render_template('expiry_report.html',
        expired=expired,
        expiring_soon=expiring_soon,
        expired_value=expired_value,
        expiring_value=expiring_value,
        today=today
    )


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    flash('Page not found.', 'warning')
    if current_user.is_authenticated and current_user.is_superadmin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('dashboard'))


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    flash('An internal error occurred. Please try again.', 'danger')
    if current_user.is_authenticated and current_user.is_superadmin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('dashboard'))


# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)