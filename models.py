"""
Database Models for Medical Store Management System
Multi-Tenant Architecture
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta, timezone

db = SQLAlchemy()


class Store(db.Model):
    """Store model - represents a tenant"""
    __tablename__ = 'stores'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    license_no = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships - with cascade delete
    users = db.relationship('User', backref='store', lazy=True, cascade='all, delete')
    medicines = db.relationship('Medicine', backref='store', lazy=True, cascade='all, delete')
    sales = db.relationship('Sale', backref='store', lazy=True, cascade='all, delete')

    def __repr__(self):
        return f'<Store {self.name}>'


class User(UserMixin, db.Model):
    """User model for authentication - belongs to a store"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='staff')
    # Roles: 'superadmin' (platform admin), 'owner' (store owner), 'staff' (store staff)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True, index=True)
    # store_id is NULL only for superadmin
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_staff(self):
        return self.role == 'staff'

    def get_store_id(self):
        """Get the store_id for this user. Returns None for superadmin."""
        return self.store_id

    def __repr__(self):
        return f'<User {self.username}>'


class Medicine(db.Model):
    """Medicine model for inventory management - scoped to a store"""
    __tablename__ = 'medicines'

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

    COUNTABLE_TYPES = ['tablet', 'capsule', 'suppository']

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    generic_name = db.Column(db.String(200), nullable=True)
    medicine_type = db.Column(db.String(50), nullable=False, default='tablet')
    units_per_pack = db.Column(db.Integer, nullable=True)
    batch_no = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    sale_items = db.relationship(
        'SaleItem', backref='medicine', lazy=True, passive_deletes=True
    )

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
        return self.medicine_type in self.COUNTABLE_TYPES

    @property
    def type_display(self):
        for code, name in self.MEDICINE_TYPES:
            if code == self.medicine_type:
                return name
        return self.medicine_type.title()

    @property
    def total_units(self):
        if self.is_countable and self.units_per_pack:
            return self.quantity * self.units_per_pack
        return self.quantity


class Sale(db.Model):
    """Sale model - scoped to a store"""
    __tablename__ = 'sales'
    __table_args__ = (
        db.UniqueConstraint('store_id', 'invoice_no', name='uq_store_invoice'),
    )

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    invoice_no = db.Column(db.String(50), nullable=False)
    sale_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    customer_name = db.Column(db.String(200), nullable=True)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    items = db.relationship(
        'SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan'
    )
    creator = db.relationship('User', backref='sales', lazy=True)

    @staticmethod
    def generate_invoice_no(store_id):
        """Generate invoice number scoped to store"""
        today = datetime.now()
        prefix = f'S{store_id}-{today.strftime("%Y%m%d")}'
        last_sale = Sale.query.filter(
            Sale.invoice_no.like(f'{prefix}%')
        ).order_by(Sale.id.desc()).first()

        if last_sale:
            last_num = int(last_sale.invoice_no.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'{prefix}-{new_num:04d}'


class SaleItem(db.Model):
    """Sale Item model - inherits store scope from Sale"""
    __tablename__ = 'sale_items'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    medicine_id = db.Column(
        db.Integer,
        db.ForeignKey('medicines.id', ondelete="RESTRICT"),
        nullable=False
    )
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    # Relationship to Store
    store = db.relationship('Store', backref='sale_items')