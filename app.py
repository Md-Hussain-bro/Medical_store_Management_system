"""
Medical Store Management System
Main Application File
"""
import sys
import webbrowser
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

from models import db, User, Medicine, Sale, SaleItem

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

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


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


def init_db():
    """Initialize database and create default users"""
    db.create_all()

    # Create default admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

    # Create default staff user
    if not User.query.filter_by(username='staff').first():
        staff = User(username='staff', role='staff')
        staff.set_password('staff123')
        db.session.add(staff)

    db.session.commit()
    print("Database initialized successfully!")


# 🔥 This runs in BOTH local and Gunicorn
with app.app_context():
    init_db()


# Context processor
@app.context_processor
def inject_now():
    return {'now': datetime.now(), 'today': date.today()}

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    """Redirect to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ==================== DASHBOARD ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Display main dashboard with statistics"""
    # Get statistics - only active medicines
    total_medicines = Medicine.query.filter(Medicine.is_active == True).count()
    
    low_stock_medicines = Medicine.query.filter(
        db.and_(
            Medicine.is_active == True,
            Medicine.quantity < 10
        )
    ).all()
    low_stock_count = len(low_stock_medicines)
    
    # Get expiring medicines (within 30 days) - only active
    expiry_date_threshold = date.today() + timedelta(days=30)
    expiring_medicines = Medicine.query.filter(
        db.and_(
            Medicine.is_active == True,
            Medicine.expiry_date <= expiry_date_threshold,
            Medicine.expiry_date >= date.today()
        )
    ).all()
    expiring_count = len(expiring_medicines)
    
    # Get today's sales
    today = date.today()
    today_sales = Sale.query.filter(
        db.func.date(Sale.sale_date) == today
    ).all()
    today_revenue = sum(sale.total_amount for sale in today_sales)
    today_sales_count = len(today_sales)
    
    # Get total stock value - only active medicines
    medicines = Medicine.query.filter(Medicine.is_active == True).all()
    total_stock_value = sum(m.quantity * m.purchase_price for m in medicines)
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
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
@login_required
def inventory():
    """Display all active medicines in inventory"""
    search = request.args.get('search', '').strip()
    
    if search:
        medicines = Medicine.query.filter(
            db.and_(
                Medicine.is_active == True,  # Only active medicines
                db.or_(
                    Medicine.name.ilike(f'%{search}%'),
                    Medicine.generic_name.ilike(f'%{search}%'),
                    Medicine.batch_no.ilike(f'%{search}%')
                )
            )
        ).order_by(Medicine.name).all()
    else:
        medicines = Medicine.query.filter(
            Medicine.is_active == True  # Only active medicines
        ).order_by(Medicine.name).all()
    
    return render_template('inventory.html', medicines=medicines, search=search)


@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_medicine():
    """Add new medicine to inventory"""
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
            
            # Validation
            if not name or not batch_no or not expiry_date:
                flash('Please fill in all required fields.', 'danger')
                return render_template('add_medicine.html')
            
            if quantity < 0:
                flash('Quantity cannot be negative.', 'danger')
                return render_template('add_medicine.html')
            
            if purchase_price < 0 or selling_price < 0:
                flash('Prices cannot be negative.', 'danger')
                return render_template('add_medicine.html')
            
            # Get medicine type and units per pack
            medicine_type = request.form.get('medicine_type', 'tablet').strip()
            units_per_pack = request.form.get('units_per_pack', '').strip()
            units_per_pack = int(units_per_pack) if units_per_pack else None
            
            # Create new medicine
            medicine = Medicine(
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
@login_required
def edit_medicine(id):
    """Edit existing medicine"""
    medicine = Medicine.query.get_or_404(id)
    
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
            
            # Validation
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
@login_required
def delete_medicine(id):
    """Soft delete medicine - marks as inactive instead of deleting"""
    medicine = Medicine.query.get_or_404(id)
    
    try:
        name = medicine.name
        medicine.is_active = False  # Soft delete - just mark as inactive
        db.session.commit()
        flash(f'Medicine "{name}" removed from inventory successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing medicine: {str(e)}', 'danger')
    
    return redirect(url_for('inventory'))


# ==================== SALES ROUTES ====================

@app.route('/sales')
@login_required
def sales():
    """Display sales page"""
    return render_template('sales.html')


@app.route('/api/search-medicine')
@login_required
def search_medicine():
    """API endpoint to search active medicines only"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 1:
        return jsonify([])
    
    medicines = Medicine.query.filter(
        db.and_(
            Medicine.is_active == True,  # Only active medicines
            Medicine.quantity > 0,
            Medicine.expiry_date >= date.today(),
            db.or_(
                Medicine.name.ilike(f'%{query}%'),
                Medicine.batch_no.ilike(f'%{query}%')
            )
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'generic_name': m.generic_name,
        'batch_no': m.batch_no,
        'quantity': m.quantity,
        'selling_price': m.selling_price,
        'expiry_date': m.expiry_date.strftime('%Y-%m-%d')
    } for m in medicines])


@app.route('/api/process-sale', methods=['POST'])
@login_required
def process_sale():
    """Process a sale transaction"""
    try:
        data = request.get_json()
        cart_items = data.get('items', [])
        customer_name = data.get('customer_name', '').strip()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        # Validate stock availability
        for item in cart_items:
            medicine = Medicine.query.get(item['medicine_id'])
            if not medicine:
                return jsonify({
                    'success': False, 
                    'message': f'Medicine not found'
                })
            if medicine.quantity < item['quantity']:
                return jsonify({
                    'success': False, 
                    'message': f'Insufficient stock for {medicine.name}'
                })
        
        # Create sale
        invoice_no = Sale.generate_invoice_no()
        total_amount = sum(item['subtotal'] for item in cart_items)
        
        sale = Sale(
            invoice_no=invoice_no,
            customer_name=customer_name if customer_name else None,
            total_amount=total_amount,
            created_by=current_user.id
        )
        db.session.add(sale)
        db.session.flush()
        
        # Create sale items and update stock
        for item in cart_items:
            medicine = Medicine.query.get(item['medicine_id'])
            
            sale_item = SaleItem(
                sale_id=sale.id,
                medicine_id=item['medicine_id'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                subtotal=item['subtotal']
            )
            db.session.add(sale_item)
            
            # Reduce stock
            medicine.quantity -= item['quantity']
        
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
@login_required
def view_bill(sale_id):
    """View/Print bill"""
    sale = Sale.query.get_or_404(sale_id)
    return render_template('bill.html', sale=sale)


# ==================== REPORTS ROUTES ====================

@app.route('/reports')
@login_required
def reports():
    """Display reports menu"""
    return render_template('reports.html')


@app.route('/reports/daily')
@login_required
def daily_report():
    """Display daily sales report"""
    report_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    try:
        selected_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    except:
        selected_date = date.today()
    
    sales = Sale.query.filter(
        db.func.date(Sale.sale_date) == selected_date
    ).order_by(Sale.sale_date.desc()).all()
    
    total_revenue = sum(sale.total_amount for sale in sales)
    total_items = sum(len(sale.items) for sale in sales)
    
    return render_template('daily_report.html',
        sales=sales,
        selected_date=selected_date,
        total_revenue=total_revenue,
        total_sales=len(sales),
        total_items=total_items
    )


@app.route('/reports/date-range')
@login_required
def date_range_report():
    """Display date range sales report"""
    from_date = request.args.get('from_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    except:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    
    sales = Sale.query.filter(
        db.func.date(Sale.sale_date) >= start_date,
        db.func.date(Sale.sale_date) <= end_date
    ).order_by(Sale.sale_date.desc()).all()
    
    total_revenue = sum(sale.total_amount for sale in sales)
    
    # Daily breakdown
    daily_data = {}
    for sale in sales:
        day = sale.sale_date.strftime('%Y-%m-%d')
        if day not in daily_data:
            daily_data[day] = {'count': 0, 'revenue': 0}
        daily_data[day]['count'] += 1
        daily_data[day]['revenue'] += sale.total_amount
    
    return render_template('date_range_report.html',
        sales=sales,
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_revenue,
        total_sales=len(sales),
        daily_data=daily_data
    )


@app.route('/reports/stock')
@login_required
def stock_report():
    """Display current stock report - only active medicines"""
    medicines = Medicine.query.filter(
        Medicine.is_active == True
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
@login_required
def expiry_report():
    """Display medicines expiring within 30 days - only active"""
    today = date.today()
    threshold = today + timedelta(days=30)
    
    # Already expired - only active medicines
    expired = Medicine.query.filter(
        db.and_(
            Medicine.is_active == True,
            Medicine.expiry_date < today,
            Medicine.quantity > 0
        )
    ).order_by(Medicine.expiry_date).all()
    
    # Expiring within 30 days - only active medicines
    expiring_soon = Medicine.query.filter(
        db.and_(
            Medicine.is_active == True,
            Medicine.expiry_date >= today,
            Medicine.expiry_date <= threshold,
            Medicine.quantity > 0
        )
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
    """Handle 404 errors"""
    flash('Page not found.', 'warning')
    return redirect(url_for('dashboard'))


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    flash('An internal error occurred. Please try again.', 'danger')
    return redirect(url_for('dashboard'))


# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

