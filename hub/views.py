import json
from datetime import datetime

from flask import render_template, session, redirect, request, url_for, jsonify
import requests
from six.moves.urllib.parse import urlencode

from hub import app, db, auth0_API, auth0, stripe
from hub.models import User
from hub.decorators import requires_auth

# Controllers API
@app.route('/')
def home():
    return redirect("/dashboard")


@app.route('/callback')
def callback_handling():
    resp = auth0.authorized_response()
    if resp is None:
        raise AuthError({'code': request.args['error'],
                         'description': request.args['error_description']}, 401)

    url = 'https://' + app.config['AUTH0_DOMAIN'] + '/userinfo'
    headers = {'authorization': 'Bearer ' + resp['access_token']}
    resp = requests.get(url, headers=headers)
    userinfo = resp.json()

    session[app.config['JWT_PAYLOAD']] = userinfo

    session[app.config['PROFILE_KEY']] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    id = id_from_userinfo(userinfo)

    user = User.query.get(id)
    if not user:
      user = User(username = id, auth0_id = userinfo['sub'])
      db.session.add(user)
      db.session.commit()

    return redirect('/dashboard')

def id_from_userinfo(userinfo):
    return userinfo.get("email") or (userinfo.get("name") + " " + userinfo.get("sub"))

@app.route('/verify', methods = ['POST'])
def verify():
    user = User.query.get(clipper_id=request.form.get("clipper"))
    return jsonify({"active": user.active})


@app.route('/login')
def login():
    return auth0.authorize(callback=app.config['AUTH0_CALLBACK_URL'])


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True, _scheme='https'), 'client_id': app.config['AUTH0_CLIENT_ID']}
    return redirect(auth0.base_url + '/v2/logout?' + urlencode(params))


@app.route('/dashboard')
@requires_auth
def dashboard():
    user = User.query.get(id_from_userinfo(session[app.config["JWT_PAYLOAD"]]))
    if user.stripe_id:
        customer = stripe.Customer.retrieve(user.stripe_id)
        subscription = stripe.Subscription.list(limit=1, customer=customer.id).data[0]
        invoices = stripe.Invoice.list(customer=customer.id).data
        for invoice in invoices:
            invoice.date = datetime.fromtimestamp(invoice.date).strftime('%m/%d/%Y')
        return render_template('dashboard.html',
                           userinfo=session['profile']['user_id'],
                           user=user,
                           customer=customer,
                           subscription=subscription,
                           invoices=invoices)
    else:
        return render_template('dashboard.html',
                               userinfo=session['profile']['user_id'],
                               payload=session[app.config['JWT_PAYLOAD']],
                               user=user)

@app.route("/discount", methods = ['POST'])
@requires_auth
def discount():
    discount = request.form.get("discount")
    user = User.query.get(id_from_userinfo(session[app.config["JWT_PAYLOAD"]]))
    customer = stripe.Customer.retrieve(user.stripe_id)
    subscription = stripe.Subscription.list(limit=1, customer=customer.id).data[0]
    subscription.coupon = discount
    subscription.save()
    return redirect("/dashboard")


@app.route("/clipper", methods = ['POST'])
@requires_auth
def clipper():
    clipper = request.form.get("clipper")
    user = User.query.get(id_from_userinfo(session[app.config["JWT_PAYLOAD"]]))
    user.clipper_id = clipper
    db.session.add(user)
    db.session.commit()
    return redirect("/dashboard")


@app.route("/save", methods = ['POST'])
@requires_auth
def save():
    source = request.form.get("stripeSource")
    user = User.query.get(id_from_userinfo(session[app.config["JWT_PAYLOAD"]]))
    if user.stripe_id:
        customer = stripe.Customer.retrieve(user.stripe_id)
        customer.source = source
    else:
        customer = stripe.Customer.create(
            email=user.username,
            source=source,
        )

    # we only have one plan so lets grab that
    plan = stripe.Plan.list(limit=1).data[0]

    first = datetime.today().replace(day=1, hour=0, minute=0, second=0)
    
    if first.month == 12:
      first = first.replace(month=1, year=first.year+1)
    else:
      first = first.replace(month=first.month+1)

    subscription = stripe.Subscription.create(
      customer=customer.id,
      items=[{'plan': plan.id}],
      trial_end=round(first.timestamp()),
    )
    user.stripe_id = customer.id
    db.session.add(user)
    db.session.commit()
    return redirect('/dashboard')
