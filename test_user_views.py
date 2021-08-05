"""User views tests."""

# run these tests like:
#
#    python -m unittest test_user_views.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

from models import db, User, Message, Follows, Likes
from bs4 import BeautifulSoup

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY
import pdb

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False

class UserViewsTestCase(TestCase):
    """Test User views functionality"""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 8989
        self.testuser.id = self.testuser_id

        self.u1 = User.signup("abc", "test1@test.com", "password", None)
        self.u1_id = 778
        self.u1.id = self.u1_id
        self.u2 = User.signup("efg", "test2@test.com", "password", None)
        self.u2_id = 884
        self.u2.id = self.u2_id
        self.u3 = User.signup("hij", "test3@test.com", "password", None)
        self.u4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_list_users(self):
        """Ensure that the /users path generates a list of all users"""

        with self.client as client:
            resp = client.get('/users')
            self.assertEqual(resp.status_code, 200)

            self.assertIn('@testuser', str(resp.data))
            self.assertIn('@abc', str(resp.data))
            self.assertIn('@efg', str(resp.data))
            self.assertIn('@hij', str(resp.data))
            self.assertIn('@testing', str(resp.data))

    def setup_likes(self):
        """Send messages to the database"""

        m1 = Message(text="testuser message1", user_id=self.testuser.id)
        m2 = Message(text="testuser message2", user_id=self.testuser.id)
        m3 = Message(id=3333, text="likeable message3", user_id=self.u1.id)

        db.session.add_all([m1, m2, m3])
        db.session.commit()

        l1 = Likes(user_id=self.testuser.id, message_id=3333)

        db.session.add(l1)
        db.session.commit()

    
    def test_users_show(self):
        """Test that loading specific user page works"""

        with self.client as client:
            resp = client.get('/users/8989')
            self.assertEqual(resp.status_code, 200)

            self.assertIn('<h4 id="sidebar-username">@testuser</h4>', str(resp.data))
    
    def test_users_show_with_likes(self):
        """Test that loading a specific user page with likes correctly shows the number of liked messages"""

        self.setup_likes()

        with self.client as client:
            resp = client.get(f"/users/{self.testuser_id}")
            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # messages
            self.assertIn("2", found[0].text)
            # following
            self.assertIn("0", found[1].text)
            # followers
            self.assertIn("0", found[2].text)
            # likes
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        m = Message(id=1234, text="add like message", user_id=self.u1.id)
        db.session.add(m)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                # This signs in a user
                sess[CURR_USER_KEY] = self.testuser_id 

            resp = client.post("/users/add_like/1234", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==1234).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser_id)

    def test_remove_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text=="likeable message3").one()
        self.assertIsNotNone(m)
        self.assertNotEqual(m.user_id, self.testuser_id)

        l = Likes.query.filter(
            Likes.user_id == self.testuser_id and Likes.message_id==m.id
        ).one()

        # Ensures that testuser likes the likeable message
        self.assertIsNotNone(l)

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = client.post(f"/users/remove_like/{m.id}", follow_redirects = True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==m.id).all()
            # test that like was removed
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text=="likeable message3").one()
        self.assertIsNotNone(m)

        like_count = Likes.query.count()

        with self.client as client:
            resp = client.post(f"/users/add_like/{m.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # Ensure number of likes has not changed since making the request
            self.assertEqual(like_count, Likes.query.count())
    
    def setup_followers(self):
        f1 = Follows(user_being_followed_id=self.u1_id, user_following_id=self.testuser_id)
        f2 = Follows(user_being_followed_id=self.u2_id, user_following_id=self.testuser_id)
        f3 = Follows(user_being_followed_id=self.testuser_id, user_following_id=self.u1_id)

        db.session.add_all([f1,f2,f3])
        db.session.commit()

    def test_show_user_with_follows(self):

        self.setup_followers()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")
            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # messages
            self.assertIn("0", found[0].text)
            # following
            self.assertIn("2", found[1].text)
            # followers
            self.assertIn("1", found[2].text)
            # likes
            self.assertIn("0", found[3].text)

    def test_show_following(self):

        self.setup_followers()

        with self.client as c:
            with c.session_transaction() as sess:
                 sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get(f"/users/{self.testuser_id}/following")
            self.assertEqual(resp.status_code, 200)

            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_show_followers(self):

        self.setup_followers()

        with self.client as c:
            with c.session_transaction() as sess:
                 sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get(f"/users/{self.testuser_id}/followers")
            self.assertEqual(resp.status_code, 200)

            self.assertIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_unauthorized_following_page_access(self):
        
        self.setup_followers()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        
        self.setup_followers()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))