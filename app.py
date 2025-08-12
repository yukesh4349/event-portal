from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://yukesh:yukesh123@yukesh.rewjjgv.mongodb.net/event_portal"
app.config["SECRET_KEY"] = "change_this_secret"
mongo = PyMongo(app)

@app.route('/')
def index():
    etype = request.args.get('type','')
    date = request.args.get('date','')
    query = {}
    if etype:
        query['event_type'] = etype
    if date:
        query['date'] = date
    events = list(mongo.db.events.find(query).sort('date', 1))
    types = mongo.db.events.distinct('event_type')
    return render_template('index.html', events=events, types=types, selected_type=etype, selected_date=date)

@app.route('/create', methods=['GET','POST'])
def create_event():
    if request.method == 'POST':
        title = request.form.get('title','')
        description = request.form.get('description','')
        date = request.form.get('date','')
        event_type = request.form.get('event_type','')
        limit = int(request.form.get('limit') or 0)
        doc = dict(title=title, description=description, date=date, event_type=event_type, limit=limit, created_at=datetime.utcnow().isoformat())
        mongo.db.events.insert_one(doc)
        flash('Event created','success')
        return redirect(url_for('index'))
    return render_template('create_event.html')

@app.route('/event/<event_id>')
def event_detail(event_id):
    event = mongo.db.events.find_one({'_id': ObjectId(event_id)})
    reg_count = mongo.db.registrations.count_documents({'event_id': event_id})
    return render_template('event.html', event=event, reg_count=reg_count)

@app.route('/register/<event_id>', methods=['GET','POST'])
def register(event_id):
    event = mongo.db.events.find_one({'_id': ObjectId(event_id)})
    if not event:
        flash('Event not found','danger')
        return redirect(url_for('index'))
    reg_count = mongo.db.registrations.count_documents({'event_id': event_id})
    if request.method == 'POST':
        if reg_count >= event.get('limit', 0):
            flash('Registration full','danger')
            return redirect(url_for('event_detail', event_id=event_id))
        name = request.form.get('name','')
        email = request.form.get('email','')
        roll = request.form.get('roll','')
        reg_doc = dict(event_id=event_id, name=name, email=email, roll=roll, created_at=datetime.utcnow().isoformat())
        res = mongo.db.registrations.insert_one(reg_doc)
        return redirect(url_for('ticket', reg_id=str(res.inserted_id)))
    return render_template('register.html', event=event, reg_count=reg_count)

@app.route('/ticket/<reg_id>')
def ticket(reg_id):
    reg = mongo.db.registrations.find_one({'_id': ObjectId(reg_id)})
    if not reg:
        flash('Registration not found','danger')
        return redirect(url_for('index'))
    event = mongo.db.events.find_one({'_id': ObjectId(reg['event_id'])})
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont('Helvetica-Bold', 20)
    p.drawString(50,800,'E-Ticket')
    p.setFont('Helvetica', 12)
    p.drawString(50,770,f"Event: {event.get('title')}")
    p.drawString(50,750,f"Date: {event.get('date')}")
    p.drawString(50,730,f"Name: {reg.get('name')}")
    p.drawString(50,710,f"Email: {reg.get('email')}")
    p.drawString(50,690,f"Roll: {reg.get('roll')}")
    p.drawString(50,650,f"Registration ID: {str(reg.get('_id'))}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"ticket_{reg_id}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
