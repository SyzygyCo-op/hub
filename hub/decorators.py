from functools import wraps

from flask import redirect, session

from hub import app

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config['PROFILE_KEY'] not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated
