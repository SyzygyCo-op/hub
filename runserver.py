from os import environ as env

from hub import app
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=env.get('PORT', 4000))
