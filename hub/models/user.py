from hub import db

class User(db.Model):
  __tablename__ = "users"
  username = db.Column(db.String(), primary_key=True)
  auth0_id = db.Column(db.String(), nullable=False)
  stripe_id = db.Column(db.String())
  clipper_id = db.Column(db.String())
  active = db.Column(db.Boolean())

  def __init__(self, username, auth0_id):
    self.username = username
    self.auth0_id = auth0_id

# generalize this
  def dictify(self):
    return {
      "username": self.username,
      "auth0_id": self.auth0_id,
      "stripe_id": self.stripe_id,
      "clipper_id": self.clipper_id,
      "active": self.active,
    }

  def __repr__(self):
    return "<User %s>" % self.username


