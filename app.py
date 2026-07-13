from flask import redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'goat'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///docket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    tasks = db.relationship('Task', backref='owner', lazy=True)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('That username is already taken.')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html')


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form.get('category', 'General')
        priority = request.form.get('priority', 'Medium')
        due_date_str = request.form.get('due_date')
        due_date = datetime.strptime(
            due_date_str, '%Y-%m-%d').date() if due_date_str else None
        new_task = Task(title=title, category=category, priority=priority,
                        due_date=due_date, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_task.html', task=None)


@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        task.title = request.form['title']
        task.category = request.form.get('category', 'General')
        task.priority = request.form.get('priority', 'Medium')
        due_date_str = request.form.get('due_date')
        task.due_date = datetime.strptime(
            due_date_str, '%Y-%m-%d').date() if due_date_str else None
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_task.html', task=task)


@app.route('/complete/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        task.done = not task.done
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    status = request.args.get('status', 'all')
    query = Task.query.filter_by(user_id=current_user.id)
    if status == 'done':
        query = query.filter_by(done=True)
    elif status == 'pending':
        query = query.filter_by(done=False)
    tasks = query.order_by(Task.done, Task.due_date).all()

    total = Task.query.filter_by(user_id=current_user.id).count()
    completed = Task.query.filter_by(
        user_id=current_user.id, done=True).count()
    return render_template('dashboard.html', tasks=tasks, total=total,
                           completed=completed, filter_status=status)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='General')
    priority = db.Column(db.String(20), default='Medium')
    due_date = db.Column(db.Date, nullable=True)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
