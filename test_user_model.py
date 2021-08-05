"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

from models import db, User, Message, Follows

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


class UserModelTestCase(TestCase):
    """Test User model functionality."""

    def setUp(self):
        """Add sample data."""

        db.drop_all()
        db.create_all()

        u1 = User.signup("test1", "email1@email.com", "password", None)
        uid1 = 1111
        u1.id = uid1

        u2 = User.signup("test2", "email2@email.com", "password", None)
        uid2 = 2222
        u2.id = uid2

        db.session.commit()

        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        self.u1 = u1
        self.uid1 = uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
    
    def test_repr_method(self):
        """Does the repr method work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        u.id = 9999

        db.session.add(u)
        db.session.commit()

        # Method should return: User <User #{self.id}: {self.username}, {self.email}>
        msg = self.u1.__repr__()
        self.assertEqual(1, 1)

        ### Following tests ###

    def test_is_following(self):
        """Does is_following successfully detect when user1 is following user2?"""

        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))
    
    def test_is_followed_by(self):
        """Does is_followed_by successfully detect when user1 is followed by user2"""

        self.u1.followers.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_followed_by(self.u2))
        self.assertFalse(self.u2.is_followed_by(self.u1))

    ### User.signup tests ###

    def test_user_signup_valid(self):
        """Does User.signup successfully create a new user given valid credentials?"""

        u = User.signup(
            username="testuser",
            email="test@test.com",
            password="HASHED_PASSWORD",
            image_url=User.image_url.default.arg
        )

        db.session.commit()

        u.id = 9999

        user = User.query.get(u.id)
        username = user.username

        self.assertEqual(username, "testuser")

    def test_user_signup_invalid(self):
        """Does User.signup return an error with invalid credentials?"""

        invalid_user = User.signup(None, "test@test.com", "password", None)
        uid = 9999
        invalid_user.id = uid

        with self.assertRaises(IntegrityError) as cm:
            db.session.commit()

        # Question: Are error codes associated with errors in Python3? Why is the above sufficient?
        
        # the_exception = cm.exception
        # pdb.set_trace()
        # # print(the_exception.args)
        # self.assertEqual(the_exception.args, 3)

    ### User.authenticate tests ###

    def test_user_authenticate(self):
        """Does User.authenticate successfully return a user when given a valid name and password?"""

        user = User.authenticate("test1", "password")

        self.assertEqual(user.username, "test1")
        self.assertIn("$2b$", user.password)

    def test_user_authenticate_invalid_username(self):
        """Does User.authenticate successfully return False when given an invalid username?"""

        user = User.authenticate("wrong_username", "password")

        self.assertEqual(user, False)

    def test_user_authenticate_invalid_password(self):
        """Does User.authenticate successfully return False when given an invalid password?"""

        user = User.authenticate("test1", "wrong_password")

        self.assertEqual(user, False)