"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

from models import db, User, Message, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app
import pdb

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

class MessageModelTestCase(TestCase):
    """Teste Message model functionality"""

    def setUp(self):
        """Add sample data"""

        db.drop_all()
        db.create_all()

        user = User.signup("test1", "email1@email.com", "password", None)
        uid = 1111
        user.id = uid

        db.session.commit()

        user = User.query.get(uid)
        self.user = user
        self.uid = uid

    def tearDown(self):
        # Question: What does this line of code do?
        res = super().tearDown()
        db.session.rollback()
        return res

    ### Relationship test ###
    
    def test_message_relationship(self):
        """Test that message is successfully related to assigned user"""

        ### Question: When do you need to add attribute labels vs just insert the values?
        message = Message(
            text="This is a test message",
            user_id=self.user.id
        )

        db.session.add(message)
        db.session.commit()

        self.assertEqual(message.text, self.user.messages[0].text)

    ### Likes Test ###

    def test_message_likes(self):
        """Test that likes work correctly"""

        u = User.signup(
            username="testuser",
            email="test@test.com",
            password="HASHED_PASSWORD",
            image_url=User.image_url.default.arg
        )

        m = Message(
            text="This is a test message",
            user_id=self.user.id
        )

        db.session.add(m)
        db.session.commit()

        u.id=9999

        user = User.query.get(u.id)

        user.likes.append(m)
        db.session.commit()

        likes=Likes.query.filter(Likes.user_id==user.id).all()

        self.assertEqual(len(likes), 1)
        self.assertEqual(likes[0].message_id, m.id)