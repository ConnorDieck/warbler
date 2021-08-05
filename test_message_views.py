"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 9999
        self.testuser.id = self.testuser_id

        db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_unauthorized_add_message(self):
        """Ensures an unauthorized user can't add a message"""
        with self.client as c:
            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_add_invalid_user(self):
        """Ensures that an invalid user can't add a message"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 99999999 # does not exist

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_message_show(self):
        """Tests message show path shows message"""

        m = Message(
            id=1984,
            text="hello",
            user_id=self.testuser_id
        )

        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            m = Message.query.get(1984)
            resp = c.get(f"/messages/{m.id}")

            self.assertEqual(resp.status_code, 200)
            self.assertIn(m.text, str(resp.data))

    def test_invalid_message_show(self):
        """Tests invalid message id will return invalid status code"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get('/messages/99999', follow_redirects=True)

            self.assertEqual(resp.status_code, 500)

    def test_message_delete(self):
        """Tests delete message route"""

        m = Message(
            id=1984,
            text="hello",
            user_id=self.testuser_id
        )

        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post("/messages/1984/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            
            m = Message.query.get(1984)
            self.assertIsNone(m)

    def test_unauthorized_message_delete(self):
        """Tests that unauthorized user cannot delete message"""

        # Second user
        u = User.signup(
            username="unauthorized-user",
            email="test2@test.com",
            password="password",
            image_url=None
        )
        u.id = 456789

        # Message by testuser
        m = Message(
            id=123456,
            text="test",
            user_id=self.testuser_id
        )

        db.session.add_all([u, m])
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 456789
            
            resp = c.post("/messages/123456/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            m = Message.query.get(123456)
            self.assertIsNotNone(m)

    def test_message_delete_no_user(self):
        """Tests that an non-signed in user cannot delete a message"""

        m = Message(
            id=123456,
            text="test",
            user_id=self.testuser_id
        )

        db.session.add(m)
        db.session.commit()

        with self.client as c:
            resp = c.post("/messages/123456/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            m = Message.query.get(123456)
            self.assertIsNotNone(m)