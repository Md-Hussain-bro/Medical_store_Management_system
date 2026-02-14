/* 
 * Medical Store Management System
 * Custom CSS Styles
 */

/* ==================== ROOT VARIABLES ==================== */
:root {
    --sidebar-width: 260px;
    --sidebar-bg: #2c3e50;
    --sidebar-hover: #34495e;
    --primary-color: #3498db;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --danger-color: #e74c3c;
}

/* ==================== GENERAL STYLES ==================== */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f4f6f9;
}

/* ==================== LOGIN PAGE ==================== */
.login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
}

.login-card {
    background: white;
    border-radius: 15px;
    padding: 40px;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
}

.login-header {
    text-align: center;
    margin-bottom: 30px;
}

.login-header i {
    font-size: 4rem;
    color: var(--primary-color);
}

.login-header h2 {
    color: #2c3e50;
    margin-top: 10px;
}

.login-footer {
    margin-top: 30px;
    text-align: center;
    padding-top: 20px;
    border-top: 1px solid #eee;
}

/* ==================== SIDEBAR ==================== */
.wrapper {
    display: flex;
    width: 100%;
    min-height: 100vh;
}

.sidebar {
    width: var(--sidebar-width);
    min-height: 100vh;
    background: var(--sidebar-bg);
    color: white;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 999;
    transition: all 0.3s;
    display: flex;
    flex-direction: column;
}

.sidebar-header {
    padding: 20px;
    background: rgba(0, 0, 0, 0.1);
    text-align: center;
}

.sidebar-header h3 {
    margin: 0;
    font-size: 1.5rem;
}

.sidebar .nav {
    flex-grow: 1;
    padding: 20px 0;
}

.sidebar .nav-link {
    color: rgba(255, 255, 255, 0.8);
    padding: 12px 25px;
    display: flex;
    align-items: center;
    transition: all 0.3s;
    border-left: 3px solid transparent;
}

.sidebar .nav-link:hover {
    background: var(--sidebar-hover);
    color: white;
    border-left-color: var(--primary-color);
}

.sidebar .nav-link.active {
    background: var(--primary-color);
    color: white;
    border-left-color: white;
}

.sidebar .nav-link i {
    margin-right: 10px;
    font-size: 1.2rem;
}

.sidebar-footer {
    padding: 20px;
    background: rgba(0, 0, 0, 0.1);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-info {
    text-align: center;
}

/* ==================== MAIN CONTENT ==================== */
#content {
    width: calc(100% - var(--sidebar-width));
    margin-left: var(--sidebar-width);
    min-height: 100vh;
    transition: all 0.3s;
}

#content .navbar {
    border-bottom: 1px solid #e9ecef;
}

/* ==================== STAT CARDS ==================== */
.stat-card {
    border-radius: 10px;
    border: none;
    transition: transform 0.3s, box-shadow 0.3s;
}

.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
}

.stat-card .stat-icon {
    font-size: 3rem;
    opacity: 0.3;
}

.stat-card .card-footer {
    padding: 10px 20px;
}

/* ==================== CARDS ==================== */
.card {
    border: none;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}

.card-header {
    background: white;
    border-bottom: 1px solid #eee;
    font-weight: 600;
}

/* ==================== TABLES ==================== */
.table th {
    font-weight: 600;
    white-space: nowrap;
}

.table td {
    vertical-align: middle;
}

/* ==================== BUTTONS ==================== */
.btn {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    transition: all 0.3s;
}

.btn-group-sm .btn {
    padding: 5px 10px;
}

/* ==================== FORMS ==================== */
.form-control, .form-select {
    border-radius: 8px;
    padding: 10px 15px;
    border: 1px solid #ddd;
}

.form-control:focus, .form-select:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

/* ==================== BADGES ==================== */
.badge {
    font-weight: 500;
    padding: 5px 10px;
}

/* ==================== ALERTS ==================== */
.alert {
    border: none;
    border-radius: 10px;
}

/* ==================== REPORT CARDS ==================== */
.report-card {
    cursor: pointer;
    border: 2px solid transparent;
}

.report-card:hover {
    border-color: var(--primary-color);
}

.report-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    margin: 0 auto;
}

/* ==================== RESPONSIVE ==================== */
@media (max-width: 991.98px) {
    .sidebar {
        margin-left: calc(-1 * var(--sidebar-width));
    }
    
    .sidebar.active {
        margin-left: 0;
    }
    
    #content {
        width: 100%;
        margin-left: 0;
    }
    
    #content.active {
        margin-left: var(--sidebar-width);
    }
}

/* ==================== PRINT STYLES ==================== */
@media print {
    .sidebar {
        display: none !important;
    }
    
    #content {
        width: 100% !important;
        margin-left: 0 !important;
    }
    
    .navbar, .btn, .alert {
        display: none !important;
    }
    
    .card {
        box-shadow: none !important;
        border: 1px solid #ddd !important;
    }
}

/* ==================== ANIMATIONS ==================== */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.card {
    animation: fadeIn 0.3s ease-out;
}

/* ==================== SCROLLBAR ==================== */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
}

/* ==================== LOW STOCK HIGHLIGHT ==================== */
.table-danger {
    background-color: #ffe5e5 !important;
}

.table-warning {
    background-color: #fff8e5 !important;
}

/* ==================== GRADIENT BACKGROUNDS ==================== */
.bg-gradient-info {
    background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
}