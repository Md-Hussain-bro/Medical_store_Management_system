"""
Database Models for Medical Store Management System
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta, timezone

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Medicine(db.Model):
    """Medicine model for inventory management"""
    __tablename__ = 'medicines'
    
    # Medicine Types - for dropdown
    MEDICINE_TYPES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('powder', 'Powder'),
        ('gel', 'Gel'),
        ('lotion', 'Lotion'),
        ('balm', 'Balm'),
        ('spray', 'Spray'),
        ('suppository', 'Suppository'),
        ('patch', 'Patch'),
        ('other', 'Other')
    ]
    
    # Types that are countable (need units per pack)
    COUNTABLE_TYPES = ['tablet', 'capsule', 'suppository']
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    generic_name = db.Column(db.String(200), nullable=True)
    medicine_type = db.Column(db.String(50), nullable=False, default='tablet')  # NEW
    units_per_pack = db.Column(db.Integer, nullable=True)  # NEW - for tablets/capsules
    batch_no = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    sale_items = db.relationship('SaleItem', backref='medicine', lazy=True, passive_deletes=True)
    
    @property
    def is_low_stock(self):
        return self.quantity < 10
    
    @property
    def is_expiring_soon(self):
        return self.expiry_date <= date.today() + timedelta(days=30)
    
    @property
    def is_expired(self):
        return self.expiry_date < date.today()
    
    @property
    def stock_value(self):
        return self.quantity * self.purchase_price
    
    @property
    def is_countable(self):
        """Check if medicine type is countable (tablets, capsules, etc.)"""
        return self.medicine_type in self.COUNTABLE_TYPES
    
    @property
    def type_display(self):
        """Get display name for medicine type"""
        for code, name in self.MEDICINE_TYPES:
            if code == self.medicine_type:
                return name
        return self.medicine_type.title()
    
    @property
    def total_units(self):
        """Calculate total individual units (for countable items)"""
        if self.is_countable and self.units_per_pack:
            return self.quantity * self.units_per_pack
        return self.quantity

class Sale(db.Model):
    """Sale model"""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), unique=True, nullable=False)
    sale_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    customer_name = db.Column(db.String(200), nullable=True)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_invoice_no():
        today = datetime.now()
        prefix = today.strftime('INV%Y%m%d')
        last_sale = Sale.query.filter(
            Sale.invoice_no.like(f'{prefix}%')
        ).order_by(Sale.id.desc()).first()
        
        if last_sale:
            last_num = int(last_sale.invoice_no[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'{prefix}{new_num:04d}'


class SaleItem(db.Model):
    """Sale Item model"""
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id', ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)